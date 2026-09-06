"""Same Game Parlay (SGP) Generator — engine-backed.

Builds 4 daily SGP tickets across odds brackets. Every leg is a QUALIFYING tip from the
OkaMoney Betting Engine (user's 20 markets, all filters must pass) taken from the SAME game.
See services/okamoney_engine.py and OKAMONEY_MARKET_SPEC_USER.md.
"""
import logging
import uuid
from typing import List, Dict, Optional
from datetime import datetime

from services import okamoney_engine as engine

logger = logging.getLogger(__name__)

ODDS_BRACKETS = [
    {'name': 'Safe Bet 1', 'min': 1.90, 'max': 3.00, 'target_legs': (2, 3)},
    {'name': 'Safe Bet 2', 'min': 1.90, 'max': 3.00, 'target_legs': (2, 3)},
    {'name': 'Value Bet', 'min': 3.01, 'max': 4.00, 'target_legs': (3, 4)},
    {'name': 'High Value', 'min': 4.01, 'max': 7.00, 'target_legs': (3, 4)},
]


class SGPGenerator:
    def generate_sgp_picks(self, target_date: Optional[str] = None) -> List[Dict]:
        pool = engine.get_daily_pool(70)
        used = set()
        tickets = []
        for bracket in ODDS_BRACKETS:
            res = engine.build_same_game_ticket(
                pool, bracket['min'], bracket['max'], bracket['target_legs'], used)
            if not res:
                continue
            game, tips, combined_odds = res
            used.add(game['fixture_id'])
            legs = [{'market': t['market'], 'selection': t['selection'],
                     'odds': t['odds'], 'confidence': round(t['probability'] / 100, 2)} for t in tips]
            avg_prob = round(sum(t['probability'] for t in tips) / len(tips))
            tickets.append({
                'id': str(uuid.uuid4()),
                'type': 'SGP',
                'ticket_name': bracket['name'],
                'odds_bracket': f"{bracket['min']:.2f} - {bracket['max']:.2f}",
                'match': {'home': game['home'], 'away': game['away'], 'league': game['league'],
                          'date': game['date'], 'fixture_id': game['fixture_id']},
                'legs': legs,
                'combined_odds': combined_odds,
                'combined_confidence': avg_prob,
                'home_form': game['home_form'],
                'away_form': game['away_form'],
                'h2h': game['h2h'],
            })
        return tickets


_sgp_generator = None


def get_sgp_generator() -> SGPGenerator:
    global _sgp_generator
    if _sgp_generator is None:
        _sgp_generator = SGPGenerator()
    return _sgp_generator
