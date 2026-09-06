"""Pick generator with real API data, Option 2 filters, and Dynamic Poisson Enhancement"""
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from services.api_football import APIFootballService
from services.stats_analyzer import StatsAnalyzer
from services.dynamic_poisson import get_poisson_calculator
import random

logger = logging.getLogger(__name__)

# Target leagues (58 leagues total - 34 original + 24 new)
TARGET_LEAGUE_IDS = {
    # UEFA Competitions
    2: "UEFA Champions League",
    3: "UEFA Europa League",
    848: "UEFA Conference League",
    
    # Top 5 European
    39: "Premier League",
    140: "La Liga",
    135: "Serie A",
    78: "Bundesliga",
    61: "Ligue 1",
    
    # Top 8 European
    88: "Eredivisie",
    94: "Primeira Liga",
    144: "Belgian Pro League",
    
    # Second Tier
    40: "Championship",
    79: "Bundesliga 2",
    141: "La Liga 2",
    136: "Serie B",
    62: "Ligue 2",
    
    # Other European
    179: "Scottish Premiership",
    203: "Süper Lig",
    333: "Ukrainian Premier League",
    218: "Austrian Bundesliga",
    207: "Swiss Super League",
    197: "Greek Super League",
    119: "Danish Superliga",
    103: "Norwegian Eliteserien",
    113: "Swedish Allsvenskan",
    345: "Czech First League",
    106: "Polish Ekstraklasa",
    
    # English Lower
    41: "League One",
    42: "League Two",
    
    # International/Middle East
    307: "Saudi Pro League",
    305: "Qatar Stars League",
    301: "UAE Pro League",
    
    # NEW LEAGUES (24 additions)
    # Africa
    567: "Tanzania Premier League",
    186: "Algeria Ligue 1",
    233: "Egypt Premier League",
    288: "South Africa Premier Division",
    200: "Morocco Botola Pro",
    
    # Americas
    128: "Argentina Liga Profesional",
    71: "Brazil Serie A",
    239: "Colombia Primera A",
    262: "Mexico Liga MX",
    
    # Europe (Additional)
    244: "Finland Veikkausliiga",
    271: "Hungary NB I",
    164: "Iceland Úrvalsdeild",
    357: "Ireland Premier Division",
    362: "Lithuania A Lyga",
    365: "Latvia Virsliga",
    371: "North Macedonia First League",
    408: "Northern Ireland Premiership",
    283: "Romania Liga I",
    110: "Wales Premier League",
    
    # Asia
    98: "Japan J1 League",
    389: "Kazakhstan Premier League",
    292: "South Korea K League 1",
}

# Leagues allowed for corner markets
CORNER_LEAGUES = [
    2, 3, 848,  # UEFA
    39, 140, 135, 78, 61,  # Top 5
    88, 94, 144,  # Top 8
    40, 79, 141, 136, 62,  # Second tier
    # Additional leagues for corners
    307,  # Saudi Pro League
    197,  # Greek Super League
    179,  # Scottish Premiership
    203,  # Turkish Süper Lig
    204,  # Turkish 1. Lig
]

class PickGenerator:
    """Generate picks using real API data, filters, and Dynamic Poisson Enhancement"""
    
    # Confidence score mapping (higher = better)
    CONFIDENCE_SCORES = {
        'Very High': 4,
        'High': 3,
        'Medium': 2,
        'Low': 1
    }
    
    # Pick limits
    MIN_DAILY_PICKS = 10
    MAX_DAILY_PICKS = 50
    
    # DC U/4.5 is the bread and butter - must be at least 60% of picks
    DC_U45_MIN_PERCENTAGE = 0.60
    PRIORITY_MARKET = "DC_U3.5"
    
    def __init__(self):
        self.api = APIFootballService()
        self.analyzer = StatsAnalyzer()
        self.poisson = get_poisson_calculator()
    
    def _score_pick(self, pick: Dict) -> float:
        """
        Score a pick based on Dynamic Poisson analysis, confidence, and odds value.
        Higher score = better pick.
        
        Priority: 
        1. Poisson value rating (most important - data-driven)
        2. Confidence from stats analysis
        3. Odds value
        4. DC U/4.5 market bonus
        """
        confidence = pick.get('confidence', 'Low')
        odds = pick.get('market', {}).get('odds', 1.0)
        market_type = pick.get('market', {}).get('type', '')
        poisson_data = pick.get('poisson_analysis', {})
        
        # Poisson value score (highest weight - data-driven)
        value_rating = poisson_data.get('value_rating', {})
        poisson_score = value_rating.get('stars', 1) * 40  # 40-200 points
        
        # Add EV bonus
        ev = value_rating.get('expected_value', 0)
        if ev > 10:
            poisson_score += 30
        elif ev > 5:
            poisson_score += 20
        elif ev > 0:
            poisson_score += 10
        
        # Confidence score (from stats analysis)
        confidence_score = self.CONFIDENCE_SCORES.get(confidence, 1) * 25
        
        # Odds score: Prefer odds in sweet spot (1.30-2.00 range)
        if 1.30 <= odds <= 2.00:
            odds_score = 30  # Perfect range
        elif 1.20 <= odds < 1.30:
            odds_score = 25  # Good but low
        elif 2.00 < odds <= 2.50:
            odds_score = 20  # Good but risky
        elif odds < 1.20:
            odds_score = 10  # Too low value
        else:
            odds_score = 5  # Too risky
        
        # DC U/4.5 bonus - our priority market gets extra score
        market_bonus = 20 if market_type == self.PRIORITY_MARKET else 0
            
        return poisson_score + confidence_score + odds_score + market_bonus
    
    def _select_best_picks(self, all_picks_by_match: Dict[str, List[Dict]]) -> List[Dict]:
        """
        Select picks following these rules:
        1. ONLY TWO MARKETS ALLOWED: DC U/4.5 and 1H Corners O/3.5
        2. DC U/4.5 is priority
        3. One pick per match (best one), unless we need more to reach minimum
        4. Minimum 10 picks, Maximum 50 picks
        
        Args:
            all_picks_by_match: Dictionary mapping fixture_id to list of picks
            
        Returns:
            List of selected picks (10-50 picks)
        """
        # ONLY ALLOWED MARKETS (4 markets)
        ALLOWED_MARKETS = {'DC_U3.5', 'O0.5_2H', 'U1.5_1H', 'O1.5_1H'}
        
        # Separate picks by market type - FILTER OUT UNWANTED MARKETS
        dc_picks = []
        team_o05_2h_picks = []
        u15_1h_picks = []
        o15_1h_picks = []
        
        for fixture_id, picks in all_picks_by_match.items():
            for pick in picks:
                market_type = pick.get('market', {}).get('type', '')
                
                # Only keep allowed markets
                if market_type == 'DC_U3.5':
                    dc_picks.append(pick)
                elif market_type == 'O0.5_2H':
                    team_o05_2h_picks.append(pick)
                elif market_type == 'U1.5_1H':
                    u15_1h_picks.append(pick)
                elif market_type == 'O1.5_1H':
                    o15_1h_picks.append(pick)
                # All other markets are IGNORED
        
        logger.info(f"Total candidates: {len(dc_picks)} DC U/3.5, {len(team_o05_2h_picks)} O0.5 2H Goals, {len(u15_1h_picks)} U1.5 1H, {len(o15_1h_picks)} O1.5 1H")
        
        # Sort all lists by score (best first)
        dc_picks = sorted(dc_picks, key=lambda p: self._score_pick(p), reverse=True)
        team_o05_2h_picks = sorted(team_o05_2h_picks, key=lambda p: self._score_pick(p), reverse=True)
        u15_1h_picks = sorted(u15_1h_picks, key=lambda p: self._score_pick(p), reverse=True)
        o15_1h_picks = sorted(o15_1h_picks, key=lambda p: self._score_pick(p), reverse=True)
        
        selected_picks = []
        used_fixtures = set()
        
        # ============================================
        # ALLOCATION STRATEGY: Equal 25% for each market
        # If market can't fill, redistribute to market with most candidates
        # If no market can absorb, leave slots VACANT
        # ============================================
        TARGET_PER_MARKET = int(self.MAX_DAILY_PICKS * 0.25)  # 12-13 picks each
        
        logger.info(f"Target allocation: 25% each = {TARGET_PER_MARKET} picks per market")
        
        # Market data structure for smart redistribution
        markets = {
            'O1.5_1H': {'picks': o15_1h_picks, 'selected': 0, 'name': 'O1.5 1H'},
            'U1.5_1H': {'picks': u15_1h_picks, 'selected': 0, 'name': 'U1.5 1H'},
            'DC_U3.5': {'picks': dc_picks, 'selected': 0, 'name': 'DC U/3.5'},
            'O0.5_2H': {'picks': team_o05_2h_picks, 'selected': 0, 'name': 'Over 0.5 2H Goals'},
        }
        
        # ============================================
        # PHASE 1: Fill each market up to 25% target
        # ============================================
        total_unfilled = 0
        
        for market_id, market_data in markets.items():
            picks_list = market_data['picks']
            selected_count = 0
            
            for pick in picks_list:
                if selected_count >= TARGET_PER_MARKET:
                    break
                fixture_id = str(pick.get('fixture_id', ''))
                
                if fixture_id not in used_fixtures:
                    selected_picks.append(pick)
                    used_fixtures.add(fixture_id)
                    selected_count += 1
            
            market_data['selected'] = selected_count
            unfilled = TARGET_PER_MARKET - selected_count
            total_unfilled += unfilled
            
            logger.info(f"Phase 1 - {market_data['name']}: {selected_count}/{TARGET_PER_MARKET} (unfilled: {unfilled})")
        
        # ============================================
        # PHASE 2: Redistribute unfilled slots to market with MOST remaining candidates
        # If no market can absorb, leave slots VACANT
        # ============================================
        if total_unfilled > 0:
            logger.info(f"Phase 2 - Redistributing {total_unfilled} unfilled slots to markets with most candidates...")
            
            # Calculate remaining candidates for each market (not yet selected)
            for market_id, market_data in markets.items():
                remaining = []
                for pick in market_data['picks']:
                    fixture_id = str(pick.get('fixture_id', ''))
                    if fixture_id not in used_fixtures:
                        remaining.append(pick)
                market_data['remaining'] = remaining
                market_data['remaining_count'] = len(remaining)
            
            # Redistribute slot by slot to market with most remaining candidates
            slots_redistributed = 0
            slots_left_vacant = 0
            
            for _ in range(total_unfilled):
                # Find market with most remaining candidates
                best_market = None
                best_count = 0
                
                for market_id, market_data in markets.items():
                    if market_data['remaining_count'] > best_count:
                        best_count = market_data['remaining_count']
                        best_market = market_id
                
                if best_market and best_count > 0:
                    # Add one pick from best market
                    pick = markets[best_market]['remaining'].pop(0)
                    markets[best_market]['remaining_count'] -= 1
                    
                    fixture_id = str(pick.get('fixture_id', ''))
                    selected_picks.append(pick)
                    used_fixtures.add(fixture_id)
                    markets[best_market]['selected'] += 1
                    slots_redistributed += 1
                else:
                    # No market can absorb - leave slot VACANT
                    slots_left_vacant += 1
            
            if slots_redistributed > 0:
                logger.info(f"  Redistributed {slots_redistributed} slots to markets with capacity")
            if slots_left_vacant > 0:
                logger.info(f"  Left {slots_left_vacant} slots VACANT (no qualifying picks)")
        
        # ============================================
        # NO PHASE 3 - We don't force fill anymore
        # If filters are strict, we accept fewer picks
        # ============================================
        
        # ============================================
        # FINAL STATS
        # ============================================
        final_o15_1h = len([p for p in selected_picks if p.get('market', {}).get('type') == 'O1.5_1H'])
        final_u15_1h = len([p for p in selected_picks if p.get('market', {}).get('type') == 'U1.5_1H'])
        final_dc = len([p for p in selected_picks if p.get('market', {}).get('type') == 'DC_U3.5'])
        final_team = len([p for p in selected_picks if p.get('market', {}).get('type') == 'O0.5_2H'])
        
        total = len(selected_picks)
        vacant = self.MAX_DAILY_PICKS - total
        
        logger.info(f"Final selection: {total} picks (max: {self.MAX_DAILY_PICKS}, vacant: {vacant})")
        if total > 0:
            logger.info(f"  O1.5 1H: {final_o15_1h} picks ({final_o15_1h/total*100:.0f}%) [target: 25%]")
            logger.info(f"  U1.5 1H: {final_u15_1h} picks ({final_u15_1h/total*100:.0f}%) [target: 25%]")
            logger.info(f"  DC U/3.5: {final_dc} picks ({final_dc/total*100:.0f}%) [target: 25%]")
            logger.info(f"  Over 0.5 2H Goals: {final_team} picks ({final_team/total*100:.0f}%) [target: 25%]")
        
        # Sort final picks by score for display
        selected_picks = sorted(selected_picks, key=lambda p: self._score_pick(p), reverse=True)
        
        return selected_picks
        
    def generate_daily_picks(self, hours_ahead: int = 24, max_matches: int = 100) -> List[Dict]:
        """Generate picks for next N hours
        
        Args:
            hours_ahead: Hours to look ahead (default 24)
            max_matches: Maximum matches to analyze (default 10 for FREE plan)
            
        Returns:
            List of qualified picks
        """
        logger.info(f"Generating picks for next {hours_ahead} hours...")
        logger.info(f"Max matches to analyze: {max_matches} (FREE plan optimization)")
        
        # Get fixtures for next 24 hours
        now = datetime.utcnow()
        date_from = now.strftime('%Y-%m-%d')
        date_to = (now + timedelta(hours=hours_ahead)).strftime('%Y-%m-%d')
        
        fixtures = self.api.get_fixtures_range(date_from, date_to)
        logger.info(f"Found {len(fixtures)} total fixtures")
        
        # Filter to our target leagues
        target_fixtures = [
            f for f in fixtures 
            if f['league']['id'] in TARGET_LEAGUE_IDS
        ]
        logger.info(f"Filtered to {len(target_fixtures)} target league fixtures")
        
        # Prioritize by league importance (UEFA, Top 5, etc.)
        priority_leagues = [2, 3, 848, 39, 140, 135, 78, 61]  # UEFA + Top 5
        
        priority_fixtures = [f for f in target_fixtures if f['league']['id'] in priority_leagues]
        other_fixtures = [f for f in target_fixtures if f['league']['id'] not in priority_leagues]
        
        # Take top fixtures from priority leagues first
        fixtures_to_analyze = (priority_fixtures + other_fixtures)[:max_matches]
        
        logger.info(f"Analyzing top {len(fixtures_to_analyze)} matches...")
        
        # Generate ALL picks from fixtures, grouped by match
        all_picks_by_match = {}
        
        for i, fixture in enumerate(fixtures_to_analyze, 1):
            fixture_id = str(fixture['fixture']['id'])
            match_name = f"{fixture['teams']['home']['name']} vs {fixture['teams']['away']['name']}"
            logger.info(f"Analyzing match {i}/{len(fixtures_to_analyze)}: {match_name}")
            
            fixture_picks = self._analyze_fixture(fixture)
            
            if fixture_picks:
                all_picks_by_match[fixture_id] = fixture_picks
                logger.info(f"  Generated {len(fixture_picks)} candidate picks from this match")
            else:
                logger.info(f"  No qualifying picks from this match")
        
        total_candidates = sum(len(picks) for picks in all_picks_by_match.values())
        logger.info(f"Generated {total_candidates} total candidate picks from {len(all_picks_by_match)} matches")
        
        # Apply selection logic: DC U/4.5 priority (60%), 1 pick per match, min 10 max 50
        selected_picks = self._select_best_picks(all_picks_by_match)
        
        logger.info(f"✅ Final selection: {len(selected_picks)} picks (min {self.MIN_DAILY_PICKS}, max {self.MAX_DAILY_PICKS})")
        return selected_picks
        
    def _analyze_fixture(self, fixture: Dict) -> List[Dict]:
        """Analyze a fixture and generate picks with Dynamic Poisson Enhancement"""
        picks = []
        
        fixture_id = fixture['fixture']['id']
        league_id = fixture['league']['id']
        league_name = fixture['league']['name']
        season = fixture['league']['season']
        
        home_team_id = fixture['teams']['home']['id']
        away_team_id = fixture['teams']['away']['id']
        home_team_name = fixture['teams']['home']['name']
        away_team_name = fixture['teams']['away']['name']
        
        # Get odds (bet_id: 1=Match Winner, 5=Goals O/U, 8=Both Teams Score)
        odds_data = self.api.get_odds(fixture_id, bet_id=1)
        
        if not odds_data:
            return picks  # No odds available
            
        # Extract odds from response
        bookmakers = odds_data.get('bookmakers', [])
        if not bookmakers:
            return picks
            
        # Get first bookmaker's odds
        bets = bookmakers[0].get('bets', [])
        if not bets:
            return picks
            
        values = bets[0].get('values', [])
        odds_dict = {v['value']: float(v['odd']) for v in values}
        
        # Get team statistics
        home_stats = self.api.get_team_statistics(home_team_id, league_id, season)
        away_stats = self.api.get_team_statistics(away_team_id, league_id, season)
        
        if not home_stats or not away_stats:
            return picks  # No stats available
            
        # Extract key statistics
        home_stats_dict = self._extract_stats(home_stats)
        away_stats_dict = self._extract_stats(away_stats)
        
        # Get H2H
        h2h = self.api.get_h2h(home_team_id, away_team_id, last=5)
        
        # ============================================
        # DYNAMIC POISSON ENHANCEMENT
        # ============================================
        poisson_analysis = self._run_dynamic_poisson_analysis(
            fixture, home_stats_dict, away_stats_dict, h2h, odds_dict
        )
        
        # ============================================
        # FOUR MARKETS: O1.5 1H, U1.5 1H, DC U/4.5, Over 0.5 2H Goals
        # ============================================
        
        # Market 1: Over 1.5 First Half Goals
        picks.extend(self._analyze_over_1_5_1h_markets(
            fixture, odds_dict, home_stats_dict, away_stats_dict, h2h, poisson_analysis
        ))
        
        # Market 2: Under 1.5 First Half Goals
        picks.extend(self._analyze_under_1_5_1h_markets(
            fixture, odds_dict, home_stats_dict, away_stats_dict, h2h, poisson_analysis
        ))
        
        # Market 3: DC U/4.5 (Double Chance + Under 3.5)
        picks.extend(self._analyze_dc_markets(
            fixture, odds_dict, home_stats_dict, away_stats_dict, h2h, poisson_analysis
        ))
        
        # Market 4: Team Over 0.5 Second Half Goals
        picks.extend(self._analyze_team_o05_2h_markets(
            fixture, odds_dict, home_stats_dict, away_stats_dict, h2h, poisson_analysis
        ))
        
        return picks
    
    def _run_dynamic_poisson_analysis(self, fixture: Dict, home_stats: Dict, 
                                       away_stats: Dict, h2h: List[Dict], 
                                       odds_dict: Dict) -> Dict:
        """Run Dynamic Poisson analysis for a fixture"""
        try:
            # Prepare home team data for Poisson
            home_team_data = {
                'id': fixture['teams']['home']['id'],
                'name': fixture['teams']['home']['name'],
                'goals_avg': home_stats.get('goals_avg', 1.5),
                'goals_conceded_avg': home_stats.get('conceded_avg', 1.2),
                'home_goals_avg': home_stats.get('goals_avg', 1.5) * 1.1,  # Home boost estimate
                'away_goals_avg': home_stats.get('goals_avg', 1.5) * 0.9,
                'recent_matches': self._extract_recent_form(h2h, fixture['teams']['home']['id']),
                'days_since_last_match': 4  # Default estimate
            }
            
            # Prepare away team data for Poisson
            away_team_data = {
                'id': fixture['teams']['away']['id'],
                'name': fixture['teams']['away']['name'],
                'goals_avg': away_stats.get('goals_avg', 1.2),
                'goals_conceded_avg': away_stats.get('conceded_avg', 1.3),
                'home_goals_avg': away_stats.get('goals_avg', 1.2) * 1.1,
                'away_goals_avg': away_stats.get('goals_avg', 1.2) * 0.9,  # Away penalty estimate
                'recent_matches': self._extract_recent_form(h2h, fixture['teams']['away']['id']),
                'days_since_last_match': 4
            }
            
            # Prepare H2H data for Poisson
            h2h_data = self._prepare_h2h_for_poisson(h2h)
            
            # Match context
            match_context = {
                'home_context': {},
                'away_context': {}
            }
            
            # Prepare bookmaker odds for Poisson
            bookmaker_odds = {
                'home_win': odds_dict.get('Home', 2.0),
                'draw': odds_dict.get('Draw', 3.5),
                'away_win': odds_dict.get('Away', 3.0),
                'dc_1x_u45': 1.35,  # Estimated - actual would come from API
                'dc_x2_u45': 1.40,
                'over_2_5': odds_dict.get('Over 2.5', 1.90),
                'under_2_5': odds_dict.get('Under 2.5', 1.90)
            }
            
            # Run Dynamic Poisson analysis
            analysis = self.poisson.analyze_match(
                home_team=home_team_data,
                away_team=away_team_data,
                h2h_data=h2h_data,
                match_context=match_context,
                bookmaker_odds=bookmaker_odds
            )
            
            return analysis
            
        except Exception as e:
            logger.warning(f"Poisson analysis failed: {e}")
            return {}
    
    def _extract_recent_form(self, h2h: List[Dict], team_id: int) -> List[Dict]:
        """Extract recent form data for a team"""
        form = []
        for match in h2h[:5] if h2h else []:
            home_id = match.get('teams', {}).get('home', {}).get('id')
            home_goals = match.get('goals', {}).get('home', 0) or 0
            away_goals = match.get('goals', {}).get('away', 0) or 0
            
            if home_id == team_id:
                result = 'W' if home_goals > away_goals else ('D' if home_goals == away_goals else 'L')
                form.append({
                    'goals_for': home_goals,
                    'goals_against': away_goals,
                    'result': result
                })
            else:
                result = 'W' if away_goals > home_goals else ('D' if away_goals == home_goals else 'L')
                form.append({
                    'goals_for': away_goals,
                    'goals_against': home_goals,
                    'result': result
                })
        return form
    
    def _prepare_h2h_for_poisson(self, h2h: List[Dict]) -> List[Dict]:
        """Prepare H2H data in format required by Poisson calculator"""
        h2h_data = []
        for match in h2h[:5] if h2h else []:
            h2h_data.append({
                'home_id': match.get('teams', {}).get('home', {}).get('id'),
                'away_id': match.get('teams', {}).get('away', {}).get('id'),
                'home_goals': match.get('goals', {}).get('home', 0) or 0,
                'away_goals': match.get('goals', {}).get('away', 0) or 0
            })
        return h2h_data
        
    def _extract_stats(self, stats_response: Dict) -> Dict:
        """Extract key statistics from API response"""
        if not stats_response or 'fixtures' not in stats_response:
            return {}
            
        fixtures_stats = stats_response.get('fixtures', {})
        goals_stats = stats_response.get('goals', {})
        clean_sheet_stats = stats_response.get('clean_sheet', {})
        failed_to_score_stats = stats_response.get('failed_to_score', {})
        
        # Calculate averages
        played = fixtures_stats.get('played', {}).get('total', 0)
        if played == 0:
            return {}
            
        goals_for = goals_stats.get('for', {}).get('total', {}).get('total', 0)
        goals_against = goals_stats.get('against', {}).get('total', {}).get('total', 0)
        
        # Extract clean sheets and failed to score
        clean_sheets = clean_sheet_stats.get('total', 0) if clean_sheet_stats else 0
        failed_to_score = failed_to_score_stats.get('total', 0) if failed_to_score_stats else 0
        
        # Calculate last 3 games average (estimate from overall if not available)
        goals_avg = goals_for / played if played > 0 else 0
        # Estimate last 3 with slight variation
        last_3_goals_avg = goals_avg * 0.95  # Slight estimate
        
        # Estimate high-scoring games (games with 4+ total goals)
        # This is an approximation based on averages
        avg_total = goals_avg + (goals_against / played if played > 0 else 0)
        high_scoring_estimate = max(0, min(5, int((avg_total - 2.5) * 2))) if avg_total > 2.5 else 0
        
        return {
            'goals_avg': goals_avg,
            'conceded_avg': goals_against / played if played > 0 else 0,
            'corners_avg': 5.0,  # Placeholder - API-SPORTS doesn't have corner stats easily accessible
            'played': played,
            # NEW: Enhanced statistics for improved filters
            'clean_sheets': clean_sheets,
            'failed_to_score': failed_to_score,
            'last_3_goals_avg': last_3_goals_avg,
            'high_scoring_games': high_scoring_estimate
        }
        
    def _analyze_dc_markets(self, fixture: Dict, odds: Dict, home_stats: Dict, 
                           away_stats: Dict, h2h: List[Dict], poisson_analysis: Dict = None) -> List[Dict]:
        """Analyze Double Chance + Under 3.5 with NEW 5 MANDATORY FILTERS + Poisson"""
        picks = []
        
        # Get league ID for context filter
        league_id = fixture['league']['id']
        home_team = fixture['teams']['home']['name']
        away_team = fixture['teams']['away']['name']
        
        # Get Poisson probabilities
        poisson_probs = poisson_analysis.get('probabilities', {}) if poisson_analysis else {}
        poisson_value = poisson_analysis.get('value_ratings', {}) if poisson_analysis else {}
        combined_markets = poisson_probs.get('combined_markets', {})
        
        # Extract win probabilities for filter 1
        home_win_prob = poisson_probs.get('home_win', 0)
        away_win_prob = poisson_probs.get('away_win', 0)
        under_35_prob = poisson_probs.get('under_3_5', combined_markets.get('under_3_5', 0))
        
        # DC + U/3.5 analysis with NEW 5 FILTERS + Poisson
        # Pass odds dict so we can check betting odds for favourite selection
        # Note: API returns keys like 'Home', 'Away', 'Draw'
        home_odds_value = odds.get('Home', odds.get('home', 0)) or 0
        away_odds_value = odds.get('Away', odds.get('away', 0)) or 0
        draw_odds_value = odds.get('Draw', odds.get('draw', 0)) or 0
        
        odds_for_analysis = {
            'home_win': float(home_odds_value) if home_odds_value else 0,
            'away_win': float(away_odds_value) if away_odds_value else 0,
            'draw': float(draw_odds_value) if draw_odds_value else 0
        }
        
        # Log odds for debugging
        logger.info(f"  DC Analysis odds: Home={odds_for_analysis['home_win']}, Away={odds_for_analysis['away_win']}")
        
        dc_u35_analysis = self.analyzer.analyze_dc_u35_enhanced(
            home_stats, away_stats, h2h, league_id=league_id,
            poisson_probs={'home_win': home_win_prob, 'away_win': away_win_prob, 
                          'under_3_5': under_35_prob},
            odds=odds_for_analysis
        )
        
        # Only qualify if ALL 5 filters passed
        qualifies = dc_u35_analysis['qualifies']
        
        if qualifies:
            # Get DC selection from analysis (1X or X2)
            dc_selection = dc_u35_analysis.get('dc_selection', '1X')
            
            # Build selection string
            selection = f"{dc_selection} & Under 3.5"
            
            # Estimate odds
            estimated_odds = random.uniform(1.35, 1.60)
            
            # Get analysis data
            score = dc_u35_analysis.get('score', 0)
            filters_passed = dc_u35_analysis.get('filters_passed', 0)
            confidence = dc_u35_analysis['confidence']
            
            # Build comprehensive reasons
            reasons = dc_u35_analysis['reasons'].copy()
            
            # Create pick with enhanced data
            pick = self._create_pick(
                fixture, "DC_U3.5", selection, estimated_odds,
                confidence, reasons,
                analysis_score=score,
                poisson_prob=under_35_prob
            )
            
            # Add analysis metadata
            pick['poisson_analysis'] = {
                'home_win_prob': home_win_prob,
                'away_win_prob': away_win_prob,
                'under_35_prob': under_35_prob,
                'expected_goals': poisson_probs.get('expected_goals', {}),
            }
            pick['enhanced_analysis'] = {
                'score': score,
                'filters_passed': filters_passed,
                'total_filters': 5,
                'dc_selection': dc_selection,
                'favoured_team': dc_u35_analysis.get('favoured_team', 'home')
            }
            
            picks.append(pick)
                
        return picks
        
    def _analyze_corner_markets(self, fixture: Dict, odds: Dict, 
                                home_stats: Dict, away_stats: Dict,
                                h2h: List[Dict] = None,
                                poisson_analysis: Dict = None) -> List[Dict]:
        """
        Analyze Team 1st Half 4+ Corners market with ENHANCED filters
        Predicts which team will get 4+ corners in the first half
        Uses H2H corner history, league context, and matchup style analysis
        """
        picks = []
        
        home_team = fixture['teams']['home']['name']
        away_team = fixture['teams']['away']['name']
        league_id = fixture['league']['id']
        
        # Analyze which team is more likely to get 4+ corners in first half
        # Using ENHANCED analysis with H2H and league context
        team_corners = self.analyzer.analyze_team_1h_corners_enhanced(
            home_stats, away_stats, 
            h2h or [], 
            home_team, away_team, 
            league_id=league_id,
            threshold=4
        )
        
        if team_corners['qualifies']:
            estimated_odds = random.uniform(1.22, 1.38)
            
            # Create pick with the recommended team
            team_name = team_corners['recommended_team']
            selection = f"{team_name} 1H 4+ Corners"
            
            # Get enhanced analysis data
            corner_probability = team_corners.get('corner_probability', 0)
            filters_passed = team_corners.get('filters_passed', 0)
            analysis_score = team_corners.get('score', 0)
            
            pick = self._create_pick(
                fixture, "TEAM_1H_4+_CORNERS", selection, estimated_odds,
                team_corners['confidence'], team_corners['reasons'],
                analysis_score=analysis_score,
                poisson_prob=corner_probability
            )
            pick['poisson_analysis'] = {}  # Corners not directly calculated by Poisson
            pick['corner_analysis'] = {
                'score': analysis_score,
                'filters_passed': filters_passed,
                'total_filters': team_corners.get('total_filters', 8),
                'home_1h_estimate': team_corners.get('home_1h_estimate', 0),
                'away_1h_estimate': team_corners.get('away_1h_estimate', 0),
                'corner_probability': corner_probability
            }
            picks.append(pick)
                
        return picks
    
    def _analyze_1x2_btts_markets(self, fixture: Dict, odds: Dict, home_stats: Dict,
                                   away_stats: Dict, h2h: List[Dict],
                                   poisson_analysis: Dict = None) -> List[Dict]:
        """
        Analyze 1X2 + BTTS (Both Teams To Score) market
        Predicts match result (Home Win, Draw, or Away Win) AND both teams scoring
        Uses ENHANCED filters for higher hit rate
        """
        picks = []
        
        home_team = fixture['teams']['home']['name']
        away_team = fixture['teams']['away']['name']
        league_id = fixture['league']['id']
        
        # Get Poisson BTTS probability if available
        poisson_probs = poisson_analysis.get('probabilities', {}) if poisson_analysis else {}
        btts_prob = poisson_probs.get('btts', {}).get('yes', 0)
        
        # Analyze 1X2 + BTTS market with ENHANCED filters
        btts_analysis = self.analyzer.analyze_1x2_btts_enhanced(
            home_stats, away_stats, h2h, home_team, away_team, league_id=league_id
        )
        
        if btts_analysis['qualifies']:
            # Estimate odds based on selection type
            selection_type = btts_analysis.get('selection_type', 'home_btts')
            
            if selection_type == 'home_btts':
                estimated_odds = random.uniform(1.80, 2.40)
            elif selection_type == 'away_btts':
                estimated_odds = random.uniform(2.50, 3.50)
            else:  # draw_btts
                estimated_odds = random.uniform(3.50, 5.00)
            
            selection = btts_analysis['recommended_selection']
            confidence = btts_analysis['confidence']
            reasons = btts_analysis['reasons']
            
            # Boost confidence if Poisson also shows high BTTS probability
            if btts_prob >= 65 and confidence in ['Medium', 'High']:
                if confidence == 'Medium':
                    confidence = 'High'
                reasons.append(f"📊 Poisson BTTS: {btts_prob}%")
            
            # Get enhanced analysis score
            analysis_score = btts_analysis.get('score', 0)
            filters_passed = btts_analysis.get('filters_passed', 0)
            
            pick = self._create_pick(
                fixture, "1X2_BTTS", selection, estimated_odds,
                confidence, reasons,
                analysis_score=analysis_score,
                poisson_prob=btts_analysis.get('btts_probability', 0)
            )
            pick['poisson_analysis'] = {
                'btts_probability': btts_analysis.get('btts_probability', 0),
                'expected_goals': poisson_probs.get('expected_goals', {})
            }
            pick['btts_analysis'] = {
                'score': analysis_score,
                'filters_passed': filters_passed,
                'total_filters': btts_analysis.get('total_filters', 11),
                'selection_type': selection_type
            }
            picks.append(pick)
                
        return picks
    
    def _analyze_over_1_5_1h_markets(self, fixture: Dict, odds: Dict, home_stats: Dict,
                                      away_stats: Dict, h2h: List[Dict],
                                      poisson_analysis: Dict = None) -> List[Dict]:
        """
        Analyze Over 1.5 First Half Goals market
        
        KEY FILTER: Combined 1H goals avg ≥ 1.4 (both teams avg ≥ 0.6 each)
        """
        picks = []
        
        home_team = fixture['teams']['home']['name']
        away_team = fixture['teams']['away']['name']
        league_id = fixture['league']['id']
        
        # Analyze O1.5 1H Goals market
        o15_1h_analysis = self.analyzer.analyze_over_1_5_first_half(
            home_stats, away_stats, h2h, home_team, away_team, league_id=league_id
        )
        
        if o15_1h_analysis['qualifies']:
            # Estimate odds for O1.5 1H (typically 1.80-2.40)
            estimated_odds = random.uniform(1.85, 2.30)
            
            selection = "Over 1.5 First Half Goals"
            confidence = o15_1h_analysis['confidence']
            reasons = o15_1h_analysis['reasons']
            
            # Get analysis data
            analysis_score = o15_1h_analysis.get('score', 0)
            filters_passed = o15_1h_analysis.get('filters_passed', 0)
            over_probability = o15_1h_analysis.get('over_probability', 0)
            
            pick = self._create_pick(
                fixture, "O1.5_1H", selection, estimated_odds,
                confidence, reasons,
                analysis_score=analysis_score,
                poisson_prob=over_probability
            )
            
            pick['o15_1h_analysis'] = {
                'score': analysis_score,
                'filters_passed': filters_passed,
                'total_filters': o15_1h_analysis.get('total_filters', 6),
                'expected_1h_goals': o15_1h_analysis.get('expected_1h_goals', 0),
                'over_probability': over_probability
            }
            picks.append(pick)
                
        return picks

    def _analyze_under_1_5_1h_markets(self, fixture: Dict, odds: Dict, home_stats: Dict,
                                       away_stats: Dict, h2h: List[Dict],
                                       poisson_analysis: Dict = None) -> List[Dict]:
        """
        Analyze Under 1.5 First Half Goals market
        
        KEY FILTER: Combined conceding average must not be over 1.1
        """
        picks = []
        
        home_team = fixture['teams']['home']['name']
        away_team = fixture['teams']['away']['name']
        league_id = fixture['league']['id']
        
        # Analyze U1.5 1H Goals market
        u15_1h_analysis = self.analyzer.analyze_under_1_5_first_half(
            home_stats, away_stats, h2h, home_team, away_team, league_id=league_id
        )
        
        if u15_1h_analysis['qualifies']:
            # Estimate odds for U1.5 1H (typically 1.35-1.65)
            estimated_odds = random.uniform(1.38, 1.58)
            
            selection = "Under 1.5 First Half Goals"
            confidence = u15_1h_analysis['confidence']
            reasons = u15_1h_analysis['reasons']
            
            # Get analysis data
            analysis_score = u15_1h_analysis.get('score', 0)
            filters_passed = u15_1h_analysis.get('filters_passed', 0)
            under_probability = u15_1h_analysis.get('under_probability', 0)
            
            pick = self._create_pick(
                fixture, "U1.5_1H", selection, estimated_odds,
                confidence, reasons,
                analysis_score=analysis_score,
                poisson_prob=under_probability
            )
            
            pick['u15_1h_analysis'] = {
                'score': analysis_score,
                'filters_passed': filters_passed,
                'total_filters': u15_1h_analysis.get('total_filters', 7),
                'expected_1h_goals': u15_1h_analysis.get('expected_1h_goals', 0),
                'under_probability': under_probability
            }
            picks.append(pick)
                
        return picks

    def _analyze_team_o05_2h_markets(self, fixture: Dict, odds: Dict, home_stats: Dict,
                                      away_stats: Dict, h2h: List[Dict],
                                      poisson_analysis: Dict = None) -> List[Dict]:
        """
        Analyze Team Over 0.5 Second Half Goals market
        
        Picks a team likely to score at least 1 goal in the second half.
        """
        picks = []
        
        home_team = fixture['teams']['home']['name']
        away_team = fixture['teams']['away']['name']
        league_id = fixture['league']['id']
        
        # Analyze Over 0.5 2H Goals market
        team_o05_2h_analysis = self.analyzer.analyze_team_over_0_5_2h(
            home_stats, away_stats, h2h, home_team, away_team, league_id=league_id
        )
        
        if team_o05_2h_analysis['qualifies']:
            # Estimate odds for Over 0.5 2H Goals (typically 1.35-1.70)
            estimated_odds = random.uniform(1.40, 1.65)
            
            selection = team_o05_2h_analysis.get('selection', f"{home_team} Over 0.5 2H Goals")
            confidence = team_o05_2h_analysis['confidence']
            reasons = team_o05_2h_analysis['reasons']
            
            # Get analysis data
            analysis_score = team_o05_2h_analysis.get('score', 0)
            filters_passed = team_o05_2h_analysis.get('filters_passed', 0)
            probability = team_o05_2h_analysis.get('probability', 0)
            
            pick = self._create_pick(
                fixture, "O0.5_2H", selection, estimated_odds,
                confidence, reasons,
                analysis_score=analysis_score,
                poisson_prob=probability
            )
            
            pick['team_o05_2h_analysis'] = {
                'score': analysis_score,
                'filters_passed': filters_passed,
                'total_filters': team_o05_2h_analysis.get('total_filters', 5),
                'team_2h_goals_est': team_o05_2h_analysis.get('team_2h_goals_est', 0),
                'selected_team': team_o05_2h_analysis.get('selected_team', ''),
                'probability': probability
            }
            picks.append(pick)
                
        return picks
        
    def _analyze_ou_markets(self, fixture: Dict, odds: Dict, home_stats: Dict,
                           away_stats: Dict, h2h: List[Dict], 
                           poisson_analysis: Dict = None) -> List[Dict]:
        """Analyze Over/Under markets with Dynamic Poisson Enhancement"""
        picks = []
        
        # Get Poisson probabilities if available
        poisson_probs = poisson_analysis.get('probabilities', {}) if poisson_analysis else {}
        over_under = poisson_probs.get('over_under', {})
        
        # O/U 2.5 - Over
        ou_over = self.analyzer.analyze_ou_25(home_stats, away_stats, 'over')
        over_2_5_prob = over_under.get('over_2_5', 0)
        
        # Qualify based on stats OR Poisson showing >55%
        if ou_over['qualifies'] or over_2_5_prob >= 55:
            # Use actual odds from API if available
            over_25_odds = odds.get('Over 2.5', random.uniform(1.50, 2.20))
            
            # Enhanced confidence from Poisson
            if over_2_5_prob >= 65:
                confidence = 'High'
            elif over_2_5_prob >= 55:
                confidence = 'Medium'
            else:
                confidence = ou_over['confidence']
            
            reasons = ou_over['reasons'].copy()
            if over_2_5_prob > 0:
                reasons.append(f"📊 Poisson: {over_2_5_prob}% for Over 2.5 goals")
            
            pick = self._create_pick(
                fixture, "OU_2.5", "Over 2.5 Goals", over_25_odds,
                confidence, reasons
            )
            pick['poisson_analysis'] = {
                'probability': over_2_5_prob,
                'expected_goals': poisson_probs.get('expected_goals', {})
            }
            picks.append(pick)
            
        # O/U 2.5 - Under
        ou_under = self.analyzer.analyze_ou_25(home_stats, away_stats, 'under')
        under_2_5_prob = over_under.get('under_2_5', 0)
        
        if ou_under['qualifies'] or under_2_5_prob >= 55:
            under_25_odds = odds.get('Under 2.5', random.uniform(1.50, 2.20))
            
            if under_2_5_prob >= 65:
                confidence = 'High'
            elif under_2_5_prob >= 55:
                confidence = 'Medium'
            else:
                confidence = ou_under['confidence']
            
            reasons = ou_under['reasons'].copy()
            if under_2_5_prob > 0:
                reasons.append(f"📊 Poisson: {under_2_5_prob}% for Under 2.5 goals")
            
            pick = self._create_pick(
                fixture, "OU_2.5", "Under 2.5 Goals", under_25_odds,
                confidence, reasons
            )
            pick['poisson_analysis'] = {
                'probability': under_2_5_prob,
                'expected_goals': poisson_probs.get('expected_goals', {})
            }
            picks.append(pick)
            
        return picks
        
    def _calculate_probability_rating(self, market_type: str, confidence: str, 
                                        analysis_score: int = 0, poisson_prob: float = 0) -> Dict:
        """
        Calculate probability percentage and star rating for a pick
        
        Factors considered:
        - Confidence level (High/Medium/Low)
        - Analysis score from filters
        - Poisson probability (if available)
        - Market type specific adjustments
        """
        # Base probability from confidence
        confidence_base = {
            'Very High': 78,
            'High': 70,
            'Medium': 60,
            'Low': 50
        }
        base_prob = confidence_base.get(confidence, 55)
        
        # Add score bonus (0-15% based on analysis score)
        if analysis_score > 0:
            score_bonus = min(15, analysis_score / 7)  # Max 15% bonus
        else:
            score_bonus = 0
        
        # Add Poisson bonus (if available)
        if poisson_prob > 0:
            if poisson_prob >= 75:
                poisson_bonus = 10
            elif poisson_prob >= 65:
                poisson_bonus = 7
            elif poisson_prob >= 55:
                poisson_bonus = 4
            else:
                poisson_bonus = 0
        else:
            poisson_bonus = 0
        
        # Market type adjustments
        market_adjustments = {
            'DC_U3.5': 3,       # Our best market - slight boost
            'TEAM_1H_4+_CORNERS': 0,
            '1X2_BTTS': -2      # More volatile market - slight reduction
        }
        market_adj = market_adjustments.get(market_type, 0)
        
        # Calculate final probability (cap at 92%)
        probability = min(92, max(45, base_prob + score_bonus + poisson_bonus + market_adj))
        
        # Convert to star rating (1-5 stars)
        if probability >= 82:
            stars = 5
            star_label = "★★★★★"
        elif probability >= 74:
            stars = 4
            star_label = "★★★★☆"
        elif probability >= 66:
            stars = 3
            star_label = "★★★☆☆"
        elif probability >= 56:
            stars = 2
            star_label = "★★☆☆☆"
        else:
            stars = 1
            star_label = "★☆☆☆☆"
        
        return {
            'probability_pct': round(probability, 1),
            'stars': stars,
            'star_display': star_label
        }
        
    def _create_pick(self, fixture: Dict, market_type: str, selection: str,
                    odds: float, confidence: str, reasons: List[str],
                    analysis_score: int = 0, poisson_prob: float = 0) -> Dict:
        """Create a pick dictionary with probability rating"""
        
        # Calculate probability and star rating
        probability_data = self._calculate_probability_rating(
            market_type, confidence, analysis_score, poisson_prob
        )
        
        return {
            'fixture_id': fixture['fixture']['id'],
            'match': {
                'home': fixture['teams']['home']['name'],
                'away': fixture['teams']['away']['name'],
                'league': fixture['league']['name'],
                'date': fixture['fixture']['date']
            },
            'market': {
                'type': market_type,
                'selection': selection,
                'odds': round(odds, 2)
            },
            'confidence': confidence,
            'probability': probability_data['probability_pct'],
            'stars': probability_data['stars'],
            'star_display': probability_data['star_display'],
            'analysis': " ".join(reasons[:2]),  # First 2 reasons
            'reasoning': " ".join(reasons),
            'stats': {
                'generated_at': datetime.utcnow().isoformat()
            }
        }
