from fastapi import FastAPI, APIRouter, Query, HTTPException, Depends, Header, Body
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import uuid
from datetime import datetime, timedelta
import random
import sys

# Add services to path
sys.path.insert(0, str(Path(__file__).parent))
from services.pick_generator import PickGenerator
from services.picks_cache import get_picks_cache
from services.results_tracker import ResultsTracker, PickResult
from services.push_notifications import PushNotificationService
from services.sgp_generator import get_sgp_generator
from services.mixed_parlay_generator import get_mixed_parlay_generator
from services.dc_singles_generator import get_dc_singles_generator
from services.games_generator import get_games_generator
from services.ticket_machine import get_ticket_machine, get_odds_ranges, get_market_types
from services.history_tracker import get_history_tracker
from services.results_tracker import get_results_tracker, PUBLIC_DAYS
from services.coin_wallet import get_coin_wallet_service, get_coin_packages, get_coin_costs
from services.whatsapp_subscription import get_whatsapp_service
from services.whatsapp_tickets_generator import get_whatsapp_tickets_generator
from services.auth_service import get_auth_service, AuthService

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Initialize services
results_tracker = ResultsTracker(db)
push_service = PushNotificationService(db)
auth_service = get_auth_service(db)
coin_service = get_coin_wallet_service(db)
whatsapp_service = get_whatsapp_service(db)

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")


# Startup event to initialize indexes
@app.on_event("startup")
async def startup_event():
    """Initialize database indexes on startup."""
    await auth_service.initialize()
    await coin_service.initialize()
    await whatsapp_service.initialize()
    logging.info("All services initialized with MongoDB indexes")


# Health check endpoint for deployment
@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration."""
    return {"status": "healthy", "service": "okamoney-api"}


@api_router.get("/health")
async def api_health_check():
    """API health check endpoint."""
    return {"status": "healthy", "service": "okamoney-api"}


# ============================================
# AUTH HELPER - Get current user from token
# ============================================

async def get_current_user(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    """Extract and verify user from Authorization header."""
    if not authorization:
        return None
    
    if not authorization.startswith("Bearer "):
        return None
    
    token = authorization[7:]  # Remove "Bearer "
    user_id = auth_service.verify_token(token)
    
    if not user_id:
        return None
    
    return await auth_service.get_user(user_id)


async def require_auth(authorization: Optional[str] = Header(None)) -> dict:
    """Require authentication - raises 401 if not authenticated."""
    user = await get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# ============================================
# AUTH MODELS
# ============================================

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: Optional[str] = ""


class LoginRequest(BaseModel):
    email: str
    password: str


# ============================================
# AUTH ENDPOINTS
# ============================================

@api_router.post("/auth/register")
async def register(data: RegisterRequest):
    """Register a new user."""
    result = await auth_service.register(
        email=data.email,
        password=data.password,
        name=data.name or ""
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@api_router.post("/auth/login")
async def login(data: LoginRequest):
    """Login and receive JWT token."""
    result = await auth_service.login(
        email=data.email,
        password=data.password
    )
    
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["error"])
    
    return result


@api_router.get("/auth/me")
async def get_me(user: dict = Depends(require_auth)):
    """Get current user info."""
    return {"user": user}


@api_router.get("/auth/check")
async def check_auth(user: Optional[dict] = Depends(get_current_user)):
    """Check if user is authenticated (doesn't require auth)."""
    if user:
        return {"authenticated": True, "user": user}
    return {"authenticated": False, "user": None}


# Models
class Match(BaseModel):
    home: str
    away: str
    league: str
    date: str

class Market(BaseModel):
    type: str  # DC_U4.5, DC_O1.5, 1H_CORNERS_O3.5, 1H_CORNERS_U5.5, OU_2.5, STRAIGHT_WIN
    selection: str
    odds: float

class Pick(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    match: Match
    market: Market
    analysis: str
    confidence: str  # High, Medium, Low
    probability: Optional[float] = None  # Probability percentage (e.g., 72.5)
    stars: Optional[int] = None  # Star rating (1-5)
    star_display: Optional[str] = None  # Star display (e.g., "★★★★☆")
    reasoning: str
    stats: Optional[dict] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserPreferences(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = "default_user"
    preferred_markets: List[str] = []
    notification_time: str = "09:00"
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class AccumulatorPick(BaseModel):
    match: Match
    market: Market
    probability: float
    confidence: str

class Accumulator(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    picks: List[AccumulatorPick]
    combined_odds: float
    target_odds_range: str
    total_probability: float
    potential_return: float  # Based on $10 stake
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Cache for mock data
_mock_picks_cache = None
_cache_timestamp = None

# Mock data generator
def generate_mock_picks(use_cache=True):
    global _mock_picks_cache, _cache_timestamp
    
    # Return cached data if available and not expired (cache for 1 hour)
    if use_cache and _mock_picks_cache and _cache_timestamp:
        if (datetime.utcnow() - _cache_timestamp).total_seconds() < 3600:
            return _mock_picks_cache
    teams = [
        # UEFA Club Competitions (Premium)
        {"home": "Real Madrid", "away": "Manchester City", "league": "UEFA Champions League"},
        {"home": "Bayern Munich", "away": "Arsenal", "league": "UEFA Champions League"},
        {"home": "Barcelona", "away": "PSG", "league": "UEFA Champions League"},
        {"home": "Inter Milan", "away": "Atletico Madrid", "league": "UEFA Champions League"},
        {"home": "Liverpool", "away": "Borussia Dortmund", "league": "UEFA Champions League"},
        {"home": "Juventus", "away": "Benfica", "league": "UEFA Champions League"},
        
        {"home": "Manchester United", "away": "Roma", "league": "UEFA Europa League"},
        {"home": "Sevilla", "away": "Lyon", "league": "UEFA Europa League"},
        {"home": "Tottenham", "away": "Ajax", "league": "UEFA Europa League"},
        {"home": "Napoli", "away": "RB Leipzig", "league": "UEFA Europa League"},
        
        {"home": "Aston Villa", "away": "Feyenoord", "league": "UEFA Conference League"},
        {"home": "Club Brugge", "away": "Celtic", "league": "UEFA Conference League"},
        {"home": "Olympiacos", "away": "Union Saint-Gilloise", "league": "UEFA Conference League"},
        
        # Top 5 European Leagues
        {"home": "Arsenal", "away": "Chelsea", "league": "Premier League"},
        {"home": "Manchester City", "away": "Liverpool", "league": "Premier League"},
        {"home": "Manchester United", "away": "Tottenham", "league": "Premier League"},
        {"home": "Real Madrid", "away": "Barcelona", "league": "La Liga"},
        {"home": "Atletico Madrid", "away": "Sevilla", "league": "La Liga"},
        {"home": "Bayern Munich", "away": "Borussia Dortmund", "league": "Bundesliga"},
        {"home": "RB Leipzig", "away": "Bayer Leverkusen", "league": "Bundesliga"},
        {"home": "Inter Milan", "away": "AC Milan", "league": "Serie A"},
        {"home": "Juventus", "away": "Napoli", "league": "Serie A"},
        {"home": "PSG", "away": "Lyon", "league": "Ligue 1"},
        {"home": "Marseille", "away": "Monaco", "league": "Ligue 1"},
        
        # Tier 1: Top 8 European (Missing 3)
        {"home": "Ajax", "away": "PSV", "league": "Eredivisie"},
        {"home": "Feyenoord", "away": "AZ Alkmaar", "league": "Eredivisie"},
        {"home": "Benfica", "away": "Porto", "league": "Primeira Liga"},
        {"home": "Sporting CP", "away": "Braga", "league": "Primeira Liga"},
        {"home": "Club Brugge", "away": "Anderlecht", "league": "Belgian Pro League"},
        {"home": "Union Saint-Gilloise", "away": "Genk", "league": "Belgian Pro League"},
        
        # Tier 2: Other Top European Leagues
        {"home": "Celtic", "away": "Rangers", "league": "Scottish Premiership"},
        {"home": "Hearts", "away": "Hibernian", "league": "Scottish Premiership"},
        {"home": "Galatasaray", "away": "Fenerbahce", "league": "Süper Lig"},
        {"home": "Besiktas", "away": "Trabzonspor", "league": "Süper Lig"},
        {"home": "Shakhtar Donetsk", "away": "Dynamo Kyiv", "league": "Ukrainian Premier League"},
        {"home": "Dnipro", "away": "Zorya", "league": "Ukrainian Premier League"},
        {"home": "Red Bull Salzburg", "away": "Sturm Graz", "league": "Austrian Bundesliga"},
        {"home": "LASK", "away": "Rapid Vienna", "league": "Austrian Bundesliga"},
        {"home": "Young Boys", "away": "Basel", "league": "Swiss Super League"},
        {"home": "Zurich", "away": "Servette", "league": "Swiss Super League"},
        {"home": "Olympiacos", "away": "Panathinaikos", "league": "Greek Super League"},
        {"home": "AEK Athens", "away": "PAOK", "league": "Greek Super League"},
        {"home": "FC Copenhagen", "away": "Brondby", "league": "Danish Superliga"},
        {"home": "Midtjylland", "away": "Nordsjaelland", "league": "Danish Superliga"},
        {"home": "Bodo/Glimt", "away": "Molde", "league": "Norwegian Eliteserien"},
        {"home": "Rosenborg", "away": "Viking", "league": "Norwegian Eliteserien"},
        {"home": "Malmo", "away": "AIK", "league": "Swedish Allsvenskan"},
        {"home": "Hacken", "away": "Djurgarden", "league": "Swedish Allsvenskan"},
        {"home": "Slavia Prague", "away": "Sparta Prague", "league": "Czech First League"},
        {"home": "Viktoria Plzen", "away": "Banik Ostrava", "league": "Czech First League"},
        {"home": "Lech Poznan", "away": "Legia Warsaw", "league": "Polish Ekstraklasa"},
        {"home": "Rakow", "away": "Pogon Szczecin", "league": "Polish Ekstraklasa"},
        
        # English Second Tier
        {"home": "Leeds United", "away": "Southampton", "league": "Championship"},
        {"home": "Leicester City", "away": "Ipswich Town", "league": "Championship"},
        
        # German Second Tier
        {"home": "Hamburg", "away": "St. Pauli", "league": "Bundesliga 2"},
        {"home": "Hertha Berlin", "away": "Schalke", "league": "Bundesliga 2"},
        
        # Spanish Second Tier
        {"home": "Real Valladolid", "away": "Sporting Gijon", "league": "La Liga 2"},
        {"home": "Real Oviedo", "away": "Eibar", "league": "La Liga 2"},
        
        # Italian Second Tier
        {"home": "Parma", "away": "Como", "league": "Serie B"},
        {"home": "Cremonese", "away": "Venezia", "league": "Serie B"},
        
        # French Second Tier
        {"home": "Bordeaux", "away": "Caen", "league": "Ligue 2"},
        {"home": "Auxerre", "away": "Metz", "league": "Ligue 2"},
        
        # English Lower Leagues
        {"home": "Portsmouth", "away": "Bolton", "league": "League One"},
        {"home": "Derby County", "away": "Barnsley", "league": "League One"},
        {"home": "Wrexham", "away": "Notts County", "league": "League Two"},
        {"home": "MK Dons", "away": "Stockport County", "league": "League Two"},
        
        # Saudi Pro League
        {"home": "Al-Hilal", "away": "Al-Nassr", "league": "Saudi Pro League"},
        {"home": "Al-Ittihad", "away": "Al-Ahli", "league": "Saudi Pro League"},
    ]
    
    markets_config = [
        {
            "type": "DC_U4.5",
            "selection": "1X & Under 4.5",
            "odds_range": (1.24, 1.48),
            "analysis": "Double chance combined with under 4.5 goals. Home team solid defensively with strong home record.",
            "reasoning": "Home team has kept clean sheets in 4/5 last games. Away team struggles to score."
        },
        {
            "type": "DC_O1.5",
            "selection": "1X & Over 1.5",
            "odds_range": (1.22, 1.34),
            "analysis": "Double chance with over 1.5 goals. Both teams consistently score.",
            "reasoning": "Last 6 H2H meetings had over 2 goals. Both teams in good attacking form."
        },
        {
            "type": "1H_CORNERS_O3.5",
            "selection": "1H Corners Over 3.5",
            "odds_range": (1.22, 1.38),
            "analysis": "First half corners over 3.5. High-pressing teams create early chances.",
            "reasoning": "Home team averages 4.2 corners in first half. Away team concedes 3.8 corners.",
            "leagues": [
                # UEFA Club Competitions (Premium)
                "UEFA Champions League", "UEFA Europa League", "UEFA Conference League",
                # Top 5 European
                "Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1",
                # Top 8 European
                "Eredivisie", "Primeira Liga", "Belgian Pro League",
                # Second Tier Major European
                "Championship", "Bundesliga 2", "La Liga 2", "Serie B", "Ligue 2"
            ]
        },
        {
            "type": "1H_CORNERS_U5.5",
            "selection": "1H Corners Under 5.5",
            "odds_range": (1.22, 1.42),
            "analysis": "First half corners under 5.5. Possession-based teams with fewer corners.",
            "reasoning": "Both teams prefer buildup play. Average 2.8 corners combined in first half.",
            "leagues": [
                # UEFA Club Competitions (Premium)
                "UEFA Champions League", "UEFA Europa League", "UEFA Conference League",
                # Top 5 European
                "Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1",
                # Top 8 European
                "Eredivisie", "Primeira Liga", "Belgian Pro League",
                # Second Tier Major European
                "Championship", "Bundesliga 2", "La Liga 2", "Serie B", "Ligue 2"
            ]
        },
        {
            "type": "OU_2.5",
            "selection": "Over 2.5 Goals",
            "odds_range": (1.50, 2.20),
            "analysis": "Over 2.5 goals expected. Both teams attacking minded with weak defenses.",
            "reasoning": "Last 5 games for both teams averaged 3.2 goals. Attacking lineups expected."
        },
        {
            "type": "STRAIGHT_WIN",
            "selection": "Home Win",
            "odds_range": (1.60, 3.50),
            "analysis": "Home team to win. Superior form and home advantage crucial.",
            "reasoning": "Home team won 8/10 last home games. Away team 2W-3D-5L on the road."
        }
    ]
    
    picks = []
    for i, team_data in enumerate(teams):
        # Determine how many picks to create for this match
        num_picks = random.randint(1, 3)
        selected_markets = random.sample(markets_config, num_picks)
        
        for market_cfg in selected_markets:
            # Check league restriction for corners
            if "leagues" in market_cfg:
                if team_data["league"] not in market_cfg["leagues"]:
                    continue
            
            match_date = datetime.utcnow() + timedelta(days=random.randint(0, 2), hours=random.randint(12, 20))
            odds = round(random.uniform(market_cfg["odds_range"][0], market_cfg["odds_range"][1]), 2)
            
            pick = Pick(
                match=Match(
                    home=team_data["home"],
                    away=team_data["away"],
                    league=team_data["league"],
                    date=match_date.isoformat()
                ),
                market=Market(
                    type=market_cfg["type"],
                    selection=market_cfg["selection"],
                    odds=odds
                ),
                analysis=market_cfg["analysis"],
                reasoning=market_cfg["reasoning"],
                confidence=random.choice(["High", "High", "Medium"]),  # Weighted towards High
                stats={
                    "home_form": "W-W-D-W-W",
                    "away_form": "W-L-D-W-L",
                    "h2h_last_5": "2-1, 1-1, 3-0, 0-2, 1-1"
                }
            )
            picks.append(pick)
    
    # Cache the results
    _mock_picks_cache = picks
    _cache_timestamp = datetime.utcnow()
    
    return picks

# Global pick generator instance
pick_generator = None

def get_pick_generator():
    """Get or create pick generator instance"""
    global pick_generator
    if pick_generator is None:
        pick_generator = PickGenerator()
    return pick_generator

# Routes
@api_router.get("/")
async def root():
    return {"message": "Soccer Betting Bot API", "version": "1.0.0", "mode": "LIVE"}

@api_router.get("/picks", response_model=List[Pick])
async def get_picks(
    market_type: Optional[str] = Query(None),
    league: Optional[str] = Query(None),
    min_odds: Optional[float] = Query(None),
    max_odds: Optional[float] = Query(None),
    refresh: Optional[bool] = Query(False)
):
    """Get daily picks from cache (fast!) - Use refresh=true to regenerate"""
    
    try:
        # Get picks from cache
        cache = get_picks_cache()
        real_picks = cache.get_picks(force_refresh=refresh)
        
        if not real_picks:
            # Fallback to mock data if cache fails
            logger.warning("Cache returned no picks, using mock data")
            picks = generate_mock_picks()
        else:
            # Convert to Pick format
            picks = []
            for pick in real_picks:
                picks.append(Pick(
                    id=str(pick.get('fixture_id', uuid.uuid4())),
                    match=Match(**pick['match']),
                    market=Market(**pick['market']),
                    analysis=pick['analysis'],
                    confidence=pick['confidence'],
                    probability=pick.get('probability'),
                    stars=pick.get('stars'),
                    star_display=pick.get('star_display'),
                    reasoning=pick['reasoning'],
                    stats=pick.get('stats', {})
                ))
    except Exception as e:
        logger.error(f"Error getting cached picks: {e}")
        # Fallback to mock data
        picks = generate_mock_picks()
    
    # Apply filters
    if market_type:
        picks = [p for p in picks if p.market.type == market_type]
    
    if league:
        picks = [p for p in picks if p.match.league == league]
    
    if min_odds is not None:
        picks = [p for p in picks if p.market.odds >= min_odds]
    
    if max_odds is not None:
        picks = [p for p in picks if p.market.odds <= max_odds]
    
    # Sort by confidence and odds
    confidence_order = {"High": 0, "Medium": 1, "Low": 2}
    picks.sort(key=lambda x: (confidence_order.get(x.confidence, 3), -x.market.odds))
    
    return picks

@api_router.get("/cache/status")
async def get_cache_status():
    """Get cache status information"""
    cache = get_picks_cache()
    return cache.get_cache_info()

@api_router.post("/cache/refresh")
async def refresh_cache():
    """Force refresh the picks cache"""
    cache = get_picks_cache()
    picks = cache.get_picks(force_refresh=True)
    return {
        "status": "success",
        "picks_generated": len(picks),
        "cache_time": cache.get_cache_info()["cache_time"]
    }

@api_router.get("/picks/{pick_id}", response_model=Pick)
async def get_pick_by_id(pick_id: str):
    """Get specific pick by ID"""
    picks = generate_mock_picks()
    pick = next((p for p in picks if p.id == pick_id), None)
    
    if not pick:
        raise HTTPException(status_code=404, detail="Pick not found")
    
    return pick

@api_router.get("/preferences", response_model=UserPreferences)
async def get_preferences():
    """Get user preferences"""
    prefs = await db.preferences.find_one({"user_id": "default_user"})
    if prefs:
        return UserPreferences(**prefs)
    
    # Return default preferences
    default_prefs = UserPreferences(
        preferred_markets=["DC_U4.5", "DC_O1.5", "OU_2.5"],
        notification_time="09:00"
    )
    return default_prefs

@api_router.post("/preferences", response_model=UserPreferences)
async def update_preferences(preferences: UserPreferences):
    """Update user preferences"""
    prefs_dict = preferences.dict()
    prefs_dict["updated_at"] = datetime.utcnow()
    
    await db.preferences.update_one(
        {"user_id": "default_user"},
        {"$set": prefs_dict},
        upsert=True
    )
    
    return preferences

def build_accumulator(picks: List[dict], target_min: float, target_max: float, 
                      used_match_ids: set, name: str) -> Optional[Accumulator]:
    """
    Build an accumulator from picks, targeting combined odds within a range.
    Picks are selected by highest probability first.
    """
    # Sort by probability (highest first) - most likely to win
    sorted_picks = sorted(
        [p for p in picks if p.get('probability', 0) > 0],
        key=lambda x: x.get('probability', 0),
        reverse=True
    )
    
    selected_picks = []
    combined_odds = 1.0
    total_prob = 1.0
    
    for pick in sorted_picks:
        # Skip if match already used in another accumulator
        match_id = f"{pick['match']['home']}_vs_{pick['match']['away']}"
        if match_id in used_match_ids:
            continue
        
        odds = pick['market'].get('odds', 1.5)
        prob = pick.get('probability', 50) / 100  # Convert to decimal
        
        # Check if adding this pick would exceed max odds
        potential_odds = combined_odds * odds
        
        if potential_odds > target_max:
            # Skip this pick, it would make odds too high
            continue
        
        # Add the pick
        selected_picks.append(AccumulatorPick(
            match=Match(
                home=pick['match']['home'],
                away=pick['match']['away'],
                league=pick['match'].get('league', 'Unknown'),
                date=pick['match'].get('date', datetime.utcnow().isoformat())
            ),
            market=Market(
                type=pick['market']['type'],
                selection=pick['market']['selection'],
                odds=odds
            ),
            probability=pick.get('probability', 50),
            confidence=pick.get('confidence', 'Medium')
        ))
        
        combined_odds = potential_odds
        total_prob *= prob
        used_match_ids.add(match_id)
        
        # Check if we've reached the target range
        if combined_odds >= target_min:
            break
    
    # Validate we have enough picks and odds are in range
    if len(selected_picks) < 2:
        return None
    
    if combined_odds < target_min:
        return None
    
    return Accumulator(
        name=name,
        picks=selected_picks,
        combined_odds=round(combined_odds, 2),
        target_odds_range=f"{target_min:.2f} - {target_max:.2f}",
        total_probability=round(total_prob * 100, 1),
        potential_return=round(10 * combined_odds, 2)  # Based on $10 stake
    )

@api_router.get("/accumulators")
async def get_accumulators():
    """
    Get two accumulators built from daily picks:
    - Accumulator 1: Combined odds 2.00 - 4.00 (safer)
    - Accumulator 2: Combined odds 4.70 - 8.00 (higher risk/reward)
    
    Picks are selected by highest probability (most likely to win).
    No pick appears in both accumulators.
    """
    try:
        # Get picks from cache
        cache = get_picks_cache()
        picks = cache.get_picks()
        
        if not picks:
            return {
                "accumulators": [],
                "message": "No picks available for accumulators"
            }
        
        used_match_ids = set()
        accumulators = []
        
        # Build Accumulator 1: Odds 2.00 - 4.00 (safer bet)
        acca1 = build_accumulator(
            picks, 
            target_min=2.00, 
            target_max=4.00, 
            used_match_ids=used_match_ids,
            name="Safe Accumulator"
        )
        if acca1:
            accumulators.append(acca1)
        
        # Build Accumulator 2: Odds 4.70 - 8.00 (higher risk/reward)
        acca2 = build_accumulator(
            picks, 
            target_min=4.70, 
            target_max=8.00, 
            used_match_ids=used_match_ids,
            name="Value Accumulator"
        )
        if acca2:
            accumulators.append(acca2)
        
        return {
            "accumulators": [a.dict() for a in accumulators],
            "total_picks_available": len(picks),
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating accumulators: {e}")
        return {
            "accumulators": [],
            "error": str(e)
        }

@api_router.get("/markets")
async def get_available_markets():
    """Get list of available betting markets"""
    return {
        "markets": [
            {"id": "O1.5_1H", "name": "Over 1.5 1H Goals", "description": "Over 1.5 First Half Goals (25%)"},
            {"id": "U1.5_1H", "name": "Under 1.5 1H Goals", "description": "Under 1.5 First Half Goals (25%)"},
            {"id": "DC_U3.5", "name": "DC + Under 3.5", "description": "Double Chance & Under 3.5 Goals (25%)"},
            {"id": "O0.5_2H", "name": "Over 0.5 2H Goals", "description": "Over 0.5 Second Half Goals (25%)"},
        ]
    }

# ============================================
# SAME GAME PARLAY (SGP) ENDPOINT
# ============================================

@api_router.get("/sgp")
async def get_sgp_picks(date: Optional[str] = None):
    """
    Get Same Game Parlay picks.
    
    Each SGP has 2-4 legs for the SAME game.
    Returns exactly 4 SGP tickets:
    - Safe Bet 1 & 2: 1.90-3.00 odds
    - Value Bet: 3.01-4.00 odds
    - High Value: 4.01-7.00 odds
    """
    try:
        sgp_gen = get_sgp_generator()
        sgp_picks = sgp_gen.generate_sgp_picks(target_date=date)
        
        return {
            "sgp_picks": sgp_picks,
            "total": len(sgp_picks),
            "generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error generating SGP picks: {e}")
        sgp_gen = get_sgp_generator()
        return {
            "sgp_picks": sgp_gen.generate_sgp_picks(),
            "total": 4,
            "generated_at": datetime.utcnow().isoformat(),
            "note": "Using mock data"
        }


@api_router.get("/mixed-parlay")
async def get_mixed_parlay_picks(date: Optional[str] = None):
    """
    Get Mixed Games Parlay picks.
    
    Each ticket has 3-5 DIFFERENT games.
    Returns exactly 2 tickets:
    - Mixed Parlay 1: 3.50-5.50 odds
    - Mixed Parlay 2: 5.51-8.00 odds
    """
    try:
        mp_gen = get_mixed_parlay_generator()
        mp_picks = mp_gen.generate_mixed_parlays(target_date=date)
        
        return {
            "mixed_parlays": mp_picks,
            "total": len(mp_picks),
            "generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error generating Mixed Parlay picks: {e}")
        mp_gen = get_mixed_parlay_generator()
        return {
            "mixed_parlays": mp_gen.generate_mixed_parlays(),
            "total": 2,
            "generated_at": datetime.utcnow().isoformat(),
            "note": "Using mock data"
        }


@api_router.get("/dc-under")
async def get_dc_under_picks(date: Optional[str] = None):
    """
    Get DC & Under 4.5 Goals single bet picks.
    
    Returns exactly 4 games with highest probability.
    """
    try:
        dc_gen = get_dc_singles_generator()
        dc_picks = dc_gen.generate_dc_under_singles(target_date=date)
        
        return {
            "dc_under_picks": dc_picks,
            "total": len(dc_picks),
            "generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error generating DC & Under picks: {e}")
        dc_gen = get_dc_singles_generator()
        return {
            "dc_under_picks": dc_gen._get_mock_dc_under(),
            "total": 4,
            "generated_at": datetime.utcnow().isoformat(),
            "note": "Using mock data"
        }


@api_router.get("/dc-over")
async def get_dc_over_picks(date: Optional[str] = None):
    """
    Get DC & Over 1.5 Goals single bet picks.
    
    Returns exactly 4 games with highest probability.
    """
    try:
        dc_gen = get_dc_singles_generator()
        dc_picks = dc_gen.generate_dc_over_singles(target_date=date)
        
        return {
            "dc_over_picks": dc_picks,
            "total": len(dc_picks),
            "generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error generating DC & Over picks: {e}")
        dc_gen = get_dc_singles_generator()
        return {
            "dc_over_picks": dc_gen._get_mock_dc_over(),
            "total": 4,
            "generated_at": datetime.utcnow().isoformat(),
            "note": "Using mock data"
        }


@api_router.post("/picks/clear-cache")
async def clear_picks_cache():
    """Clear the picks cache to force regeneration on next request"""
    from services.picks_cache import clear_cache
    clear_cache()
    return {"message": "Cache cleared successfully", "next_request_will_regenerate": True}

# ============================================
# DAILY GAMES ENDPOINT (100 GAMES)
# ============================================

# Admin secret key for private endpoints
ADMIN_SECRET_KEY = os.environ.get('ADMIN_SECRET_KEY') or 'okamoney_admin_2024'

@api_router.get("/games")
async def get_daily_games(date: Optional[str] = None, limit: int = 100):
    """
    Get daily games (up to 100) with their best 2-3 markets.
    
    Top 3 games are FREE (is_free=true), rest require subscription.
    Games are sorted by combined probability (best first).
    """
    try:
        games_gen = get_games_generator()
        games = games_gen.generate_daily_games(target_date=date, limit=limit)
        
        return {
            "games": games,
            "total": len(games),
            "free_count": 3,
            "generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error generating daily games: {e}")
        games_gen = get_games_generator()
        return {
            "games": games_gen.generate_daily_games(limit=limit),
            "total": limit,
            "free_count": 3,
            "generated_at": datetime.utcnow().isoformat(),
            "note": "Using mock data"
        }


# ============================================
# ADMIN CARDS ENDPOINT (PRIVATE)
# ============================================

@api_router.get("/admin/cards")
async def get_admin_cards(key: str = Query(..., description="Admin secret key")):
    """
    Get SGP and Mixed Parlay cards (ADMIN ONLY).
    
    Requires admin secret key for access.
    Returns Build A Bet (SGP) and Mixed Parlay cards for screenshot/sharing.
    """
    if key != ADMIN_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")
    
    try:
        sgp_gen = get_sgp_generator()
        mp_gen = get_mixed_parlay_generator()
        
        sgp_picks = sgp_gen.generate_sgp_picks()
        mixed_picks = mp_gen.generate_mixed_parlays()
        
        return {
            "build_a_bet": {
                "tickets": sgp_picks,
                "total": len(sgp_picks),
                "type": "Same Game Parlay"
            },
            "mixed_parlay": {
                "tickets": mixed_picks,
                "total": len(mixed_picks),
                "type": "Mixed Games Parlay"
            },
            "generated_at": datetime.utcnow().isoformat(),
            "admin_access": True
        }
    except Exception as e:
        logger.error(f"Error generating admin cards: {e}")
        sgp_gen = get_sgp_generator()
        mp_gen = get_mixed_parlay_generator()
        
        return {
            "build_a_bet": {
                "tickets": sgp_gen._get_mock_sgp_picks(),
                "total": 4,
                "type": "Same Game Parlay"
            },
            "mixed_parlay": {
                "tickets": mp_gen._get_mock_mixed_parlays(),
                "total": 4,
                "type": "Mixed Games Parlay"
            },
            "generated_at": datetime.utcnow().isoformat(),
            "admin_access": True,
            "note": "Using mock data"
        }

# ============================================
# PUSH NOTIFICATION ENDPOINTS
# ============================================

class PushTokenRequest(BaseModel):
    token: str
    device_info: Optional[dict] = None

class TestNotificationRequest(BaseModel):
    title: Optional[str] = "🎯 Test Notification"
    body: Optional[str] = "Push notifications are working!"

@api_router.post("/push/register")
async def register_push_token(request: PushTokenRequest):
    """
    Register a device for push notifications
    
    Token should be an Expo Push Token (ExponentPushToken[...])
    """
    result = await push_service.register_token(
        token=request.token,
        device_info=request.device_info
    )
    
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error'))
    
    return result

@api_router.post("/push/unregister")
async def unregister_push_token(request: PushTokenRequest):
    """Unregister a device from push notifications"""
    result = await push_service.unregister_token(request.token)
    return result

@api_router.post("/push/test")
async def send_test_notification(request: TestNotificationRequest):
    """
    Send a test notification to all registered devices
    (For testing purposes)
    """
    result = await push_service.send_bulk_notifications(
        title=request.title,
        body=request.body,
        data={"type": "test"}
    )
    return result

@api_router.get("/push/tokens")
async def get_registered_tokens():
    """Get count of registered push tokens"""
    tokens = await push_service.get_active_tokens()
    return {
        "count": len(tokens),
        "active": True if tokens else False
    }

# ============================================
# RESULTS TRACKING ENDPOINTS
# ============================================

class RecordResultRequest(BaseModel):
    result: str  # won, lost, void, half_won, half_lost, pending
    pick_data: Optional[dict] = None  # Full pick data to store

class BulkResultRequest(BaseModel):
    results: List[dict]  # List of {"pick_id": str, "result": str, "pick_data": dict}

@api_router.post("/picks/{pick_id}/result")
async def record_pick_result(pick_id: str, request: RecordResultRequest):
    """
    Record the result of a pick (won/lost/void)
    
    Result options: won, lost, void, half_won, half_lost, pending
    """
    try:
        result_enum = PickResult(request.result.lower())
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid result. Must be one of: {[r.value for r in PickResult]}"
        )
    
    result = await results_tracker.record_result(
        pick_id=pick_id,
        result=result_enum,
        pick_data=request.pick_data
    )
    
    return result

@api_router.get("/picks/{pick_id}/result")
async def get_pick_result(pick_id: str):
    """Get the recorded result for a specific pick"""
    result = await results_tracker.get_pick_result(pick_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="Result not found for this pick")
    
    return result

@api_router.post("/results/bulk")
async def bulk_record_results(request: BulkResultRequest):
    """Record multiple pick results at once"""
    return await results_tracker.bulk_record_results(request.results)

@api_router.get("/stats")
async def get_statistics(
    days: int = Query(30, description="Number of days to include (0 = all time)"),
    market_type: Optional[str] = Query(None, description="Filter by market type")
):
    """
    Get comprehensive betting statistics
    
    Returns:
    - Hit rate (%)
    - ROI (%)
    - Win/Loss counts
    - Streak information
    - Breakdown by confidence and market type
    """
    return await results_tracker.get_statistics(days=days, market_type=market_type)

@api_router.get("/history")
async def get_history(
    limit: int = Query(50, le=200, description="Maximum results to return"),
    offset: int = Query(0, description="Pagination offset"),
    result: Optional[str] = Query(None, description="Filter by result type")
):
    """
    Get historical picks with their results
    
    Supports pagination and filtering by result type
    """
    return await results_tracker.get_history(
        limit=limit,
        offset=offset,
        result_filter=result
    )

@api_router.get("/pending")
async def get_pending_picks():
    """Get all picks that are still pending (not yet settled)"""
    return await results_tracker.get_pending_picks()


# ============================================
# WHATSAPP GROUP SUBSCRIPTION ENDPOINTS
# ============================================

# Default mock user ID (will be replaced with auth user ID later)
MOCK_USER_ID = "demo_user_001"


@api_router.get("/whatsapp/status")
async def get_whatsapp_purchase_status():
    """
    Check if WhatsApp group purchase window is open.
    Windows are only open on 8th and 26th of each month.
    """
    try:
        status = whatsapp_service.is_purchase_window_open()
        return status
    except Exception as e:
        logger.error(f"Error checking WhatsApp status: {e}")
        return {"is_open": False, "error": str(e)}


@api_router.post("/whatsapp/purchase")
async def purchase_whatsapp_subscription(
    user_name: str = "User",
    user_email: str = None,
    user: Optional[dict] = Depends(get_current_user)
):
    """
    Purchase WhatsApp group subscription (R125).
    Only available on 8th and 26th of each month.
    Returns downloadable receipt as proof of payment.
    """
    try:
        user_id = user["id"] if user else MOCK_USER_ID
        if user:
            user_name = user.get("name", user_name)
            user_email = user.get("email", user_email)
        result = await whatsapp_service.purchase_subscription(user_id, user_name, user_email)
        return result
    except Exception as e:
        logger.error(f"Error purchasing WhatsApp subscription: {e}")
        return {"success": False, "error": str(e)}


@api_router.get("/whatsapp/subscriptions")
async def get_user_whatsapp_subscriptions(user: Optional[dict] = Depends(get_current_user)):
    """Get user's WhatsApp subscription history."""
    try:
        user_id = user["id"] if user else MOCK_USER_ID
        subscriptions = await whatsapp_service.get_user_subscriptions(user_id)
        return {"subscriptions": subscriptions}
    except Exception as e:
        logger.error(f"Error getting WhatsApp subscriptions: {e}")
        return {"subscriptions": [], "error": str(e)}


# ============================================
# ADMIN WHATSAPP VERIFICATION ENDPOINTS
# ============================================

@api_router.get("/admin/whatsapp/verify/{receipt_id}")
async def verify_whatsapp_receipt(receipt_id: str):
    """
    Admin endpoint to verify a WhatsApp subscription receipt.
    Returns receipt details if valid, or error if invalid/already used.
    """
    try:
        result = await whatsapp_service.verify_receipt(receipt_id)
        return result
    except Exception as e:
        logger.error(f"Error verifying receipt: {e}")
        return {"valid": False, "error": str(e)}


@api_router.post("/admin/whatsapp/mark-verified/{receipt_id}")
async def mark_receipt_verified(receipt_id: str):
    """
    Admin endpoint to mark a receipt as verified (user added to group).
    Prevents the same receipt from being reused.
    """
    try:
        result = await whatsapp_service.mark_as_verified(receipt_id)
        return result
    except Exception as e:
        logger.error(f"Error marking receipt verified: {e}")
        return {"success": False, "error": str(e)}


@api_router.get("/admin/whatsapp/all")
async def get_all_whatsapp_subscriptions(include_verified: bool = True):
    """
    Admin endpoint to get all WhatsApp subscriptions.
    Can filter to show only unverified (pending) subscriptions.
    """
    try:
        subscriptions = await whatsapp_service.get_all_subscriptions(include_verified)
        return {
            "subscriptions": subscriptions,
            "total": len(subscriptions),
            "pending": len([s for s in subscriptions if not s.get("verified", False)])
        }
    except Exception as e:
        logger.error(f"Error getting all subscriptions: {e}")
        return {"subscriptions": [], "error": str(e)}


# ============================================
# ADMIN WHATSAPP TICKETS GENERATOR ENDPOINTS
# ============================================

@api_router.get("/admin/whatsapp-tickets")
async def get_whatsapp_daily_tickets():
    """
    Admin endpoint to generate all 4 daily WhatsApp tickets.
    
    Returns:
    - Build A Bet (1.90-3.40 odds) - single game, multiple markets
    - Mixed Parlay (3.50-5.50 odds) - multiple games
    - Big Odds (8.00-25.00 odds) - max 12 games
    - Mega Odds (27.00-50.00 odds) - max 15 games
    """
    try:
        generator = get_whatsapp_tickets_generator()
        tickets = generator.generate_all_daily_tickets()
        return tickets
    except Exception as e:
        logger.error(f"Error generating WhatsApp tickets: {e}")
        return {"error": str(e), "tickets": []}


@api_router.get("/admin/whatsapp-tickets/build-a-bet")
async def get_whatsapp_build_a_bet():
    """Generate a single Build A Bet ticket (1.90-3.40 odds)."""
    try:
        generator = get_whatsapp_tickets_generator()
        ticket = generator.generate_build_a_bet()
        return {"ticket": ticket}
    except Exception as e:
        logger.error(f"Error generating Build A Bet: {e}")
        return {"error": str(e)}


@api_router.get("/admin/whatsapp-tickets/mixed-parlay")
async def get_whatsapp_mixed_parlay():
    """Generate a single Mixed Parlay ticket (3.50-5.50 odds)."""
    try:
        generator = get_whatsapp_tickets_generator()
        ticket = generator.generate_mixed_parlay()
        return {"ticket": ticket}
    except Exception as e:
        logger.error(f"Error generating Mixed Parlay: {e}")
        return {"error": str(e)}


@api_router.get("/admin/whatsapp-tickets/big-odds")
async def get_whatsapp_big_odds():
    """Generate a single Big Odds ticket (8.00-25.00 odds, max 12 games)."""
    try:
        generator = get_whatsapp_tickets_generator()
        ticket = generator.generate_big_odds()
        return {"ticket": ticket}
    except Exception as e:
        logger.error(f"Error generating Big Odds: {e}")
        return {"error": str(e)}


@api_router.get("/admin/whatsapp-tickets/mega-odds")
async def get_whatsapp_mega_odds():
    """Generate a single Mega Odds ticket (27.00-50.00 odds, max 15 games)."""
    try:
        generator = get_whatsapp_tickets_generator()
        ticket = generator.generate_mega_odds()
        return {"ticket": ticket}
    except Exception as e:
        logger.error(f"Error generating Mega Odds: {e}")
        return {"error": str(e)}


# ============================================
# COIN WALLET ENDPOINTS
# ============================================


@api_router.get("/wallet/balance")
async def get_wallet_balance(user: Optional[dict] = Depends(get_current_user)):
    """Get user's coin balance and wallet info."""
    try:
        user_id = user["id"] if user else MOCK_USER_ID
        balance_info = await coin_service.get_balance(user_id)
        return balance_info
    except Exception as e:
        logger.error(f"Error getting wallet balance: {e}")
        return {"balance": 0, "error": str(e)}


@api_router.get("/wallet/packages")
async def get_available_packages():
    """Get available coin packages for purchase."""
    packages = get_coin_packages()
    costs = get_coin_costs()
    return {
        "packages": list(packages.values()),
        "costs": costs,
        "disclaimer": {
            "lines": [
                "Coins are non-refundable and non-transferable.",
                "Coins expire 45 days after purchase.",
                "Each purchase resets expiry for all coins."
            ]
        }
    }


@api_router.post("/wallet/purchase")
async def purchase_coins(package_id: str, user: Optional[dict] = Depends(get_current_user)):
    """
    Purchase a coin package (mock implementation).
    In production, this initiates Payfast payment flow.
    """
    try:
        user_id = user["id"] if user else MOCK_USER_ID
        result = await coin_service.purchase_coins(user_id, package_id)
        return result
    except Exception as e:
        logger.error(f"Error purchasing coins: {e}")
        return {"success": False, "error": str(e)}


@api_router.post("/wallet/spend")
async def spend_coins(amount: int, spend_type: str, item_id: str = None, user: Optional[dict] = Depends(get_current_user)):
    """
    Spend coins on viewing tips or generating betslips.
    spend_type: 'view_tip', 'build_a_bet', 'mixed_parlay', 'ticket_machine'
    """
    try:
        user_id = user["id"] if user else MOCK_USER_ID
        result = await coin_service.spend_coins(user_id, amount, spend_type, item_id)
        return result
    except Exception as e:
        logger.error(f"Error spending coins: {e}")
        return {"success": False, "error": str(e)}


@api_router.post("/wallet/use-daily-free")
async def use_daily_free(feature: str, user: Optional[dict] = Depends(get_current_user)):
    """
    Use daily free access for subscribed users.
    feature: 'ticket_machine', 'build_a_bet', 'mixed_parlay'
    """
    try:
        user_id = user["id"] if user else MOCK_USER_ID
        result = await coin_service.use_daily_free(user_id, feature)
        return result
    except Exception as e:
        logger.error(f"Error using daily free: {e}")
        return {"success": False, "error": str(e)}


@api_router.get("/wallet/check-daily-free")
async def check_daily_free(feature: str, user: Optional[dict] = Depends(get_current_user)):
    """Check if daily free is available for a feature."""
    try:
        user_id = user["id"] if user else MOCK_USER_ID
        available = await coin_service.check_daily_free(user_id, feature)
        return {"available": available, "feature": feature}
    except Exception as e:
        logger.error(f"Error checking daily free: {e}")
        return {"available": False, "error": str(e)}


@api_router.post("/wallet/subscribe")
async def set_subscription(is_subscribed: bool, days: int = 30, user: Optional[dict] = Depends(get_current_user)):
    """
    Set user subscription status (mock implementation).
    In production, this is called after Payfast subscription confirmation.
    """
    try:
        user_id = user["id"] if user else MOCK_USER_ID
        expires = (datetime.utcnow() + timedelta(days=days)).isoformat() if is_subscribed else None
        result = await coin_service.set_subscription(user_id, is_subscribed, expires)
        return result
    except Exception as e:
        logger.error(f"Error setting subscription: {e}")
        return {"success": False, "error": str(e)}


@api_router.get("/wallet/transactions")
async def get_transactions(limit: int = 20, user: Optional[dict] = Depends(get_current_user)):
    """Get recent transaction history."""
    try:
        user_id = user["id"] if user else MOCK_USER_ID
        transactions = await coin_service.get_transaction_history(user_id, limit)
        return {"transactions": transactions}
    except Exception as e:
        logger.error(f"Error getting transactions: {e}")
        return {"transactions": [], "error": str(e)}


@api_router.post("/wallet/bonus")
async def add_bonus_coins(amount: int, reason: str = "Welcome bonus", user: Optional[dict] = Depends(get_current_user)):
    """Add bonus coins (for testing/promotions)."""
    try:
        user_id = user["id"] if user else MOCK_USER_ID
        result = await coin_service.add_bonus_coins(user_id, amount, reason)
        return result
    except Exception as e:
        logger.error(f"Error adding bonus: {e}")
        return {"success": False, "error": str(e)}


# ============================================
# YESTERDAY RESULTS ENDPOINTS
# ============================================

@api_router.get("/games/yesterday")
async def get_yesterday_games():
    """
    Get yesterday's 100 games with their results.
    
    Each game shows:
    - The original predictions that were made
    - Whether each prediction was correct (won/lost)
    - Green tick (✅) for won, red cross (❌) for lost
    """
    try:
        tracker = get_history_tracker()
        data = tracker.get_yesterday_games()
        
        if not data:
            return {
                "games": [],
                "total": 0,
                "date": (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d'),
                "message": "No historical data available for yesterday"
            }
        
        return {
            "games": data.get('games', []),
            "total": len(data.get('games', [])),
            "date": data.get('date'),
            "results_processed": data.get('results_processed', False),
            "generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching yesterday's games: {e}")
        return {
            "games": [],
            "total": 0,
            "error": str(e)
        }

# ============================================
# RESULTS TRACKER (real per-market hit-rates)
# ============================================

@api_router.get("/results/recent")
async def results_recent(days: int = PUBLIC_DAYS):
    """PUBLIC: settled/pending results for the last up-to-3 days."""
    try:
        tracker = get_results_tracker(db)
        return await tracker.get_public_recent(days)
    except Exception as e:
        logger.error(f"Error fetching recent results: {e}")
        return {"days": [], "error": str(e)}


@api_router.get("/admin/results/stats")
async def admin_results_stats(key: str = Query(...), days: int = 30):
    """ADMIN: per-market hit-rate analytics over 7/14/30/all-time (days=3650 ~ all)."""
    if key != ADMIN_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")
    tracker = get_results_tracker(db)
    return await tracker.get_admin_stats(days)


@api_router.get("/admin/results/pending")
async def admin_results_pending(key: str = Query(...), date: Optional[str] = None):
    """ADMIN: list a day's tips to settle. Defaults to yesterday."""
    if key != ADMIN_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")
    if not date:
        date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    tracker = get_results_tracker(db)
    return {"date": date, "tips": await tracker.get_day_picks(date)}


@api_router.post("/admin/results/settle")
async def admin_results_settle(key: str = Query(...), date: str = Body(...),
                               results: Dict[str, str] = Body(...)):
    """ADMIN: settle tips against real outcomes. results = {tip_id: won|lost|void}."""
    if key != ADMIN_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")
    tracker = get_results_tracker(db)
    updated = await tracker.settle(date, results, mode='manual')
    return {"success": True, "updated": updated}


@api_router.post("/admin/results/simulate")
async def admin_results_simulate(key: str = Query(...), date: Optional[str] = None):
    """ADMIN (DEMO ONLY): auto-grade a day's pending tips by probability. Clearly flagged 'simulated'."""
    if key != ADMIN_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")
    if not date:
        date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    tracker = get_results_tracker(db)
    graded = await tracker.simulate_settle(date)
    return {"success": True, "graded": graded, "mode": "simulated", "date": date}




@api_router.get("/sgp/yesterday")
async def get_yesterday_sgp():
    """
    Get yesterday's SGP (Build A Bet) tickets with overall win/loss.
    
    Each ticket shows:
    - The original legs that were predicted
    - Overall result: WON or LOST (all legs must win for ticket to win)
    """
    try:
        tracker = get_history_tracker()
        data = tracker.get_yesterday_sgp()
        
        if not data:
            return {
                "sgp_picks": [],
                "total": 0,
                "date": (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d'),
                "message": "No SGP history available for yesterday"
            }
        
        return {
            "sgp_picks": data.get('tickets', []),
            "total": len(data.get('tickets', [])),
            "date": data.get('date'),
            "results_processed": data.get('results_processed', False),
            "generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching yesterday's SGP: {e}")
        return {
            "sgp_picks": [],
            "total": 0,
            "error": str(e)
        }


@api_router.get("/mixed-parlay/yesterday")
async def get_yesterday_mixed_parlay():
    """
    Get yesterday's Mixed Parlay tickets with overall win/loss.
    
    Each ticket shows:
    - The original games/legs that were predicted
    - Overall result: WON or LOST (all legs must win for ticket to win)
    """
    try:
        tracker = get_history_tracker()
        data = tracker.get_yesterday_mixed_parlay()
        
        if not data:
            return {
                "mixed_parlays": [],
                "total": 0,
                "date": (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d'),
                "message": "No Mixed Parlay history available for yesterday"
            }
        
        return {
            "mixed_parlays": data.get('tickets', []),
            "total": len(data.get('tickets', [])),
            "date": data.get('date'),
            "results_processed": data.get('results_processed', False),
            "generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching yesterday's Mixed Parlay: {e}")
        return {
            "mixed_parlays": [],
            "total": 0,
            "error": str(e)
        }


# ============================================
# TICKET MACHINE ENDPOINTS
# ============================================

@api_router.get("/ticket-machine/options")
async def get_ticket_machine_options():
    """
    Get available odds ranges and market types for the Ticket Machine.
    
    Returns:
    - odds_ranges: Available odds brackets with labels
    - market_types: Available market types (All, Corners, BTTS, Over 2.5)
    """
    return {
        "odds_ranges": get_odds_ranges(),
        "market_types": get_market_types()
    }


@api_router.post("/ticket-machine/generate")
async def generate_ticket(
    odds_range: str = Query(..., description="Odds range: safe, value, risky, high_risk, very_high, extreme, jackpot"),
    market_type: str = Query(..., description="Market type: all, corners, btts, over25")
):
    """
    Generate a custom ticket based on selected odds range and market type.
    
    Odds Ranges:
    - safe: 1.80-3.00 (1-2 legs)
    - value: 3.01-7.00 (2-3 legs)
    - risky: 7.01-12.00 (3-4 legs)
    - high_risk: 12.01-20.00 (4-5 legs)
    - very_high: 20.01-50.00 (5-6 legs)
    - extreme: 50.01-99.00 (6-8 legs)
    - jackpot: 100+ (8+ legs)
    
    Market Types:
    - all: All available markets
    - corners: Only corner markets
    - btts: Both Teams To Score (Yes)
    - over25: Over 2.5 Total Goals
    
    NOTE: This endpoint is for subscribers only. 
    - Subscribers get 1 free ticket per day
    - Additional 4 tickets available for R15
    - All tickets expire at midnight (00:00)
    """
    try:
        machine = get_ticket_machine()
        ticket = machine.generate_ticket(odds_range, market_type)
        
        return {
            "success": True,
            "ticket": ticket,
            "message": "Ticket generated successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating ticket: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate ticket")


# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
