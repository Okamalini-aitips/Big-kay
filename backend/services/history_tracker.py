"""History Tracker Service for OkaMoney AI Tips

Stores daily predictions and tracks their results.
When API-Sports is reactivated, this will verify predictions against real outcomes.
For now, simulates realistic win/loss outcomes for mock data.

Uses in-memory storage (persists during app runtime).
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import uuid
import random

logger = logging.getLogger(__name__)


class HistoryTracker:
    """Track daily predictions and their results."""
    
    def __init__(self):
        # In-memory storage for history data
        self._games_history: Dict[str, Dict] = {}
        self._sgp_history: Dict[str, Dict] = {}
        self._mixed_history: Dict[str, Dict] = {}
    
    def store_daily_games(self, games: List[Dict], date_str: str = None) -> bool:
        """
        Store today's 100 games predictions for future reference.
        Called when generating daily games.
        """
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        self._games_history[date_str] = {
            'date': date_str,
            'stored_at': datetime.utcnow().isoformat(),
            'games': games,
            'results_processed': False
        }
        
        return True
    
    def store_sgp_tickets(self, tickets: List[Dict], date_str: str = None) -> bool:
        """Store today's SGP (Build A Bet) tickets."""
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        self._sgp_history[date_str] = {
            'date': date_str,
            'stored_at': datetime.utcnow().isoformat(),
            'tickets': tickets,
            'results_processed': False
        }
        
        return True
    
    def store_mixed_parlay_tickets(self, tickets: List[Dict], date_str: str = None) -> bool:
        """Store today's Mixed Parlay tickets."""
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        self._mixed_history[date_str] = {
            'date': date_str,
            'stored_at': datetime.utcnow().isoformat(),
            'tickets': tickets,
            'results_processed': False
        }
        
        return True
    
    def get_yesterday_games(self) -> Optional[Dict]:
        """
        Get yesterday's games with their results.
        If no stored data exists, generates realistic mock historical data.
        """
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Try to load stored predictions
        if yesterday in self._games_history:
            data = self._games_history[yesterday]
            if not data.get('results_processed', False):
                data = self._process_game_results(data)
                self._games_history[yesterday] = data
            return data
        
        # Generate mock historical data if nothing stored
        return self._generate_mock_yesterday_games(yesterday)
    
    def get_yesterday_sgp(self) -> Optional[Dict]:
        """Get yesterday's SGP tickets with overall win/loss."""
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        if yesterday in self._sgp_history:
            data = self._sgp_history[yesterday]
            if not data.get('results_processed', False):
                data = self._process_sgp_results(data)
                self._sgp_history[yesterday] = data
            return data
        
        # Generate mock SGP history
        return self._generate_mock_yesterday_sgp(yesterday)
    
    def get_yesterday_mixed_parlay(self) -> Optional[Dict]:
        """Get yesterday's Mixed Parlay tickets with overall win/loss."""
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        if yesterday in self._mixed_history:
            data = self._mixed_history[yesterday]
            if not data.get('results_processed', False):
                data = self._process_mixed_parlay_results(data)
                self._mixed_history[yesterday] = data
            return data
        
        # Generate mock Mixed Parlay history
        return self._generate_mock_yesterday_mixed_parlay(yesterday)
    
    def _process_game_results(self, data: Dict) -> Dict:
        """
        Process game results - when API is active, this will verify against real data.
        For now, simulates results based on probability.
        """
        games = data.get('games', [])
        
        for game in games:
            markets = game.get('markets', [])
            for market in markets:
                probability = market.get('probability', 65)
                won = random.random() * 100 < probability
                market['result'] = 'won' if won else 'lost'
        
        data['results_processed'] = True
        data['processed_at'] = datetime.utcnow().isoformat()
        
        return data
    
    def _process_sgp_results(self, data: Dict) -> Dict:
        """Process SGP ticket results - determines overall win/loss."""
        tickets = data.get('tickets', [])
        
        for ticket in tickets:
            legs = ticket.get('legs', [])
            all_won = True
            
            for leg in legs:
                probability = leg.get('probability', 65)
                won = random.random() * 100 < probability
                leg['result'] = 'won' if won else 'lost'
                if not won:
                    all_won = False
            
            ticket['overall_result'] = 'won' if all_won else 'lost'
        
        data['results_processed'] = True
        data['processed_at'] = datetime.utcnow().isoformat()
        
        return data
    
    def _process_mixed_parlay_results(self, data: Dict) -> Dict:
        """Process Mixed Parlay ticket results - determines overall win/loss."""
        tickets = data.get('tickets', [])
        
        for ticket in tickets:
            legs = ticket.get('legs', [])
            all_won = True
            
            for leg in legs:
                probability = leg.get('probability', 65)
                won = random.random() * 100 < probability
                leg['result'] = 'won' if won else 'lost'
                if not won:
                    all_won = False
            
            ticket['overall_result'] = 'won' if all_won else 'lost'
        
        data['results_processed'] = True
        data['processed_at'] = datetime.utcnow().isoformat()
        
        return data
    
    def _generate_mock_yesterday_games(self, date_str: str) -> Dict:
        """Generate realistic mock historical games with results."""
        
        mock_games_data = [
            {"home": "Liverpool", "away": "Arsenal", "league": "Premier League"},
            {"home": "Man City", "away": "Chelsea", "league": "Premier League"},
            {"home": "Barcelona", "away": "Real Madrid", "league": "La Liga"},
            {"home": "Bayern Munich", "away": "Dortmund", "league": "Bundesliga"},
            {"home": "Inter Milan", "away": "AC Milan", "league": "Serie A"},
            {"home": "PSG", "away": "Lyon", "league": "Ligue 1"},
            {"home": "Ajax", "away": "PSV", "league": "Eredivisie"},
            {"home": "Benfica", "away": "Porto", "league": "Primeira Liga"},
            {"home": "Juventus", "away": "Napoli", "league": "Serie A"},
            {"home": "Tottenham", "away": "Newcastle", "league": "Premier League"},
            {"home": "Celtic", "away": "Rangers", "league": "Scottish Premiership"},
            {"home": "Galatasaray", "away": "Fenerbahce", "league": "Süper Lig"},
            {"home": "Atletico Madrid", "away": "Sevilla", "league": "La Liga"},
            {"home": "RB Leipzig", "away": "Wolfsburg", "league": "Bundesliga"},
            {"home": "Roma", "away": "Lazio", "league": "Serie A"},
            {"home": "Marseille", "away": "Monaco", "league": "Ligue 1"},
            {"home": "Feyenoord", "away": "AZ Alkmaar", "league": "Eredivisie"},
            {"home": "Sporting CP", "away": "Braga", "league": "Primeira Liga"},
            {"home": "Aston Villa", "away": "West Ham", "league": "Premier League"},
            {"home": "Valencia", "away": "Villarreal", "league": "La Liga"},
        ]
        
        market_templates = [
            {'market': 'Over 2.5 Total Goals', 'selection': 'Over 2.5 Total Goals', 'odds': 1.85, 'probability': 62},
            {'market': 'Under 3.5 Total Goals', 'selection': 'Under 3.5 Total Goals', 'odds': 1.45, 'probability': 72},
            {'market': 'Both Teams To Score', 'selection': 'Both Teams To Score - Yes', 'odds': 1.78, 'probability': 60},
            {'market': 'Over 0.5 First Half Goals', 'selection': 'Over 0.5 First Half Goals', 'odds': 1.22, 'probability': 78},
            {'market': 'Over 0.5 Second Half Goals', 'selection': 'Over 0.5 Second Half Goals', 'odds': 1.28, 'probability': 76},
            {'market': 'Double Chance', 'selection': 'Double Chance 1X', 'odds': 1.32, 'probability': 75},
            {'market': 'Under 4.5 Total Goals', 'selection': 'Under 4.5 Total Goals', 'odds': 1.18, 'probability': 85},
            {'market': 'Over 1.5 Total Goals', 'selection': 'Over 1.5 Total Goals', 'odds': 1.28, 'probability': 80},
        ]
        
        games = []
        for i, match_data in enumerate(mock_games_data):
            selected_markets = random.sample(market_templates, 2)
            markets = []
            
            for market_template in selected_markets:
                market = dict(market_template)
                market['probability'] = max(55, min(90, market['probability'] + random.randint(-8, 8)))
                won = random.random() * 100 < market['probability']
                market['result'] = 'won' if won else 'lost'
                markets.append(market)
            
            combined_prob = sum(m['probability'] for m in markets) / len(markets)
            
            games.append({
                'id': str(uuid.uuid4()),
                'fixture_id': 2000 + i,
                'match': {
                    'home': match_data['home'],
                    'away': match_data['away'],
                    'league': match_data['league'],
                    'date': f"{date_str}T19:00:00"
                },
                'markets': markets,
                'combined_probability': round(combined_prob, 1),
                'home_form': ''.join(random.choices(['W', 'W', 'W', 'D', 'L'], k=5)),
                'away_form': ''.join(random.choices(['W', 'W', 'D', 'D', 'L'], k=5)),
                'is_free': i < 3,
                'rank': i + 1
            })
        
        games.sort(key=lambda x: x['combined_probability'], reverse=True)
        for i, game in enumerate(games):
            game['rank'] = i + 1
            game['is_free'] = i < 3
        
        return {
            'date': date_str,
            'stored_at': f"{date_str}T09:00:00",
            'games': games,
            'results_processed': True,
            'processed_at': datetime.utcnow().isoformat()
        }
    
    def _generate_mock_yesterday_sgp(self, date_str: str) -> Dict:
        """Generate realistic mock SGP tickets with results."""
        
        tickets = [
            {
                'id': str(uuid.uuid4()),
                'name': 'Safe Bet 1',
                'match': {
                    'home': 'Liverpool',
                    'away': 'Arsenal',
                    'league': 'Premier League'
                },
                'legs': [
                    {'market': 'Over 0.5 First Half Goals', 'selection': 'Over 0.5 First Half Goals', 'odds': 1.22, 'probability': 78},
                    {'market': 'Both Teams To Score', 'selection': 'Both Teams To Score - Yes', 'odds': 1.75, 'probability': 62},
                ],
                'combined_odds': 2.14,
                'combined_confidence': 70,
                'odds_bracket': '1.90-3.00'
            },
            {
                'id': str(uuid.uuid4()),
                'name': 'Safe Bet 2',
                'match': {
                    'home': 'Barcelona',
                    'away': 'Real Madrid',
                    'league': 'La Liga'
                },
                'legs': [
                    {'market': 'Over 1.5 Total Goals', 'selection': 'Over 1.5 Total Goals', 'odds': 1.30, 'probability': 82},
                    {'market': 'Double Chance', 'selection': 'Double Chance 1X', 'odds': 1.45, 'probability': 72},
                ],
                'combined_odds': 1.89,
                'combined_confidence': 77,
                'odds_bracket': '1.90-3.00'
            }
        ]
        
        for ticket in tickets:
            all_won = True
            for leg in ticket['legs']:
                won = random.random() * 100 < leg['probability']
                leg['result'] = 'won' if won else 'lost'
                if not won:
                    all_won = False
            ticket['overall_result'] = 'won' if all_won else 'lost'
        
        return {
            'date': date_str,
            'stored_at': f"{date_str}T09:00:00",
            'tickets': tickets,
            'results_processed': True,
            'processed_at': datetime.utcnow().isoformat()
        }
    
    def _generate_mock_yesterday_mixed_parlay(self, date_str: str) -> Dict:
        """Generate realistic mock Mixed Parlay tickets with results."""
        
        tickets = [
            {
                'id': str(uuid.uuid4()),
                'name': 'Mixed Parlay 1',
                'num_games': 3,
                'legs': [
                    {'home': 'Liverpool', 'away': 'Arsenal', 'league': 'Premier League', 'market': 'Over 2.5 Goals', 'selection': 'Over 2.5 Total Goals', 'odds': 1.85, 'probability': 62},
                    {'home': 'Barcelona', 'away': 'Real Madrid', 'league': 'La Liga', 'market': 'BTTS', 'selection': 'Both Teams To Score - Yes', 'odds': 1.72, 'probability': 60},
                    {'home': 'Bayern', 'away': 'Dortmund', 'league': 'Bundesliga', 'market': 'Over 1.5 Goals', 'selection': 'Over 1.5 Total Goals', 'odds': 1.28, 'probability': 80},
                ],
                'combined_odds': 4.08,
                'combined_confidence': 67,
                'odds_bracket': '3.50-5.50'
            },
            {
                'id': str(uuid.uuid4()),
                'name': 'Mixed Parlay 2',
                'num_games': 4,
                'legs': [
                    {'home': 'Inter', 'away': 'AC Milan', 'league': 'Serie A', 'market': 'Under 3.5 Goals', 'selection': 'Under 3.5 Total Goals', 'odds': 1.45, 'probability': 72},
                    {'home': 'PSG', 'away': 'Lyon', 'league': 'Ligue 1', 'market': 'Double Chance', 'selection': 'Double Chance 1X', 'odds': 1.30, 'probability': 75},
                    {'home': 'Ajax', 'away': 'PSV', 'league': 'Eredivisie', 'market': 'Over 0.5 1H Goals', 'selection': 'Over 0.5 First Half Goals', 'odds': 1.22, 'probability': 78},
                    {'home': 'Benfica', 'away': 'Porto', 'league': 'Primeira Liga', 'market': 'BTTS', 'selection': 'Both Teams To Score - Yes', 'odds': 1.80, 'probability': 58},
                ],
                'combined_odds': 4.15,
                'combined_confidence': 70,
                'odds_bracket': '3.50-5.50'
            },
            {
                'id': str(uuid.uuid4()),
                'name': 'Mixed Parlay 3',
                'num_games': 4,
                'legs': [
                    {'home': 'Juventus', 'away': 'Napoli', 'league': 'Serie A', 'market': 'Over 2.5 Goals', 'selection': 'Over 2.5 Total Goals', 'odds': 1.90, 'probability': 60},
                    {'home': 'Tottenham', 'away': 'Newcastle', 'league': 'Premier League', 'market': 'Over 1.5 Goals', 'selection': 'Over 1.5 Total Goals', 'odds': 1.25, 'probability': 82},
                    {'home': 'Celtic', 'away': 'Rangers', 'league': 'Scottish Prem', 'market': 'BTTS', 'selection': 'Both Teams To Score - Yes', 'odds': 1.65, 'probability': 65},
                    {'home': 'Galatasaray', 'away': 'Fenerbahce', 'league': 'Süper Lig', 'market': 'Over 2.5 Goals', 'selection': 'Over 2.5 Total Goals', 'odds': 1.80, 'probability': 62},
                ],
                'combined_odds': 7.05,
                'combined_confidence': 67,
                'odds_bracket': '5.51-8.00'
            }
        ]
        
        for ticket in tickets:
            all_won = True
            for leg in ticket['legs']:
                won = random.random() * 100 < leg['probability']
                leg['result'] = 'won' if won else 'lost'
                if not won:
                    all_won = False
            ticket['overall_result'] = 'won' if all_won else 'lost'
        
        return {
            'date': date_str,
            'stored_at': f"{date_str}T09:00:00",
            'tickets': tickets,
            'results_processed': True,
            'processed_at': datetime.utcnow().isoformat()
        }


# Singleton instance
_history_tracker = None


def get_history_tracker():
    """Get or create the history tracker singleton."""
    global _history_tracker
    if _history_tracker is None:
        _history_tracker = HistoryTracker()
    return _history_tracker
