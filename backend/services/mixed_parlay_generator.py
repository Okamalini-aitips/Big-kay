"""Mixed Games Parlay Generator — engine-backed.

Builds 4 Mixed Parlay tickets. Each leg is the best QUALIFYING tip from a DIFFERENT game
(user's 20 markets, all filters must pass, ranked by blended probability).
See services/okamoney_engine.py and OKAMONEY_MARKET_SPEC_USER.md.
"""
import logging
import uuid
from typing import List, Dict, Optional

from services import okamoney_engine as engine

logger = logging.getLogger(__name__)

ODDS_BRACKETS = [
    {'name': 'Mixed Parlay 1', 'min': 3.50, 'max': 5.00, 'target_games': (3, 4)},
    {'name': 'Mixed Parlay 2', 'min': 5.01, 'max': 6.50, 'target_games': (3, 4)},
    {'name': 'Mixed Parlay 3', 'min': 6.51, 'max': 8.00, 'target_games': (4, 6)},
    {'name': 'Mixed Parlay 4', 'min': 8.01, 'max': 12.00, 'target_games': (5, 8)},
]


class MixedParlayGenerator:
    def generate_mixed_parlays(self, target_date: Optional[str] = None) -> List[Dict]:
        pool = engine.get_daily_pool(70)
        used = set()
        tickets = []
        for bracket in ODDS_BRACKETS:
            res = engine.build_cross_game_ticket(
                pool, bracket['min'], bracket['max'], bracket['target_games'], used)
            if not res:
                continue
            sel, combined_odds = res
            legs = []
            for item in sel:
                g, t = item['game'], item['tip']
                used.add(g['fixture_id'])
                legs.append({
                    'home': g['home'], 'away': g['away'], 'league': g['league'],
                    'market': t['market'], 'selection': t['selection'],
                    'odds': t['odds'], 'confidence': round(t['probability'] / 100, 2),
                })
            avg_prob = round(sum(i['tip']['probability'] for i in sel) / len(sel))
            tickets.append({
                'id': str(uuid.uuid4()),
                'type': 'Mixed Parlay',
                'ticket_name': bracket['name'],
                'odds_bracket': f"{bracket['min']:.2f} - {bracket['max']:.2f}",
                'legs': legs,
                'combined_odds': combined_odds,
                'combined_confidence': avg_prob,
                'num_games': len(legs),
            })
        return tickets


_mixed_parlay_generator = None


def get_mixed_parlay_generator() -> MixedParlayGenerator:
    global _mixed_parlay_generator
    if _mixed_parlay_generator is None:
        _mixed_parlay_generator = MixedParlayGenerator()
    return _mixed_parlay_generator
