"""Admin WhatsApp Tickets Generator — engine-backed.

Generates the 4 daily WhatsApp tickets (Build A Bet, Mixed Parlay, Big Odds, Mega Odds).
Every leg is a QUALIFYING tip from the OkaMoney Betting Engine (user's 20 markets, all
filters must pass). See services/okamoney_engine.py and OKAMONEY_MARKET_SPEC_USER.md.
"""
import logging
import uuid
from typing import Dict, List
from datetime import datetime

from services import okamoney_engine as engine

logger = logging.getLogger(__name__)


def _match_of(g: Dict) -> Dict:
    return {'home': g['home'], 'away': g['away'], 'league': g['league'], 'date': g['date']}


def _cross_legs(sel: List[Dict]) -> List[Dict]:
    legs = []
    for item in sel:
        g, t = item['game'], item['tip']
        legs.append({
            'match': _match_of(g),
            'home': g['home'], 'away': g['away'], 'league': g['league'],
            'market': t['market'], 'selection': t['selection'], 'odds': t['odds'],
        })
    return legs


def _avg_conf(sel: List[Dict]) -> int:
    n = max(len(sel), 1)
    avg = sum(i['tip']['probability'] for i in sel) / n
    return int(round(avg * (0.97 ** (n - 1))))


class WhatsAppTicketsGenerator:
    def _pool(self):
        return engine.get_daily_pool(70)

    def generate_build_a_bet(self) -> Dict:
        """Single game, multiple qualifying markets. Target odds 1.90-3.40."""
        pool = self._pool()
        res = engine.build_same_game_ticket(pool, 1.90, 3.40, (2, 3), set())
        if res:
            game, tips, combined_odds = res
            legs = [{'market': t['market'], 'selection': t['selection'], 'odds': t['odds']} for t in tips]
            confidence = int(round(sum(t['probability'] for t in tips) / len(tips)))
            match = _match_of(game)
        else:
            match, legs, combined_odds, confidence = {'home': '-', 'away': '-', 'league': '-'}, [], 0, 0
        return {
            'id': str(uuid.uuid4()), 'type': 'Build A Bet', 'match': match, 'legs': legs,
            'combined_odds': combined_odds, 'odds_range': '1.90-3.40',
            'confidence': confidence, 'generated_at': datetime.now().isoformat(),
        }

    def generate_mixed_parlay(self) -> Dict:
        """Multiple games. Target odds 3.50-5.50."""
        pool = self._pool()
        res = engine.build_cross_game_ticket(pool, 3.50, 5.50, (3, 4), set())
        sel, combined_odds = res if res else ([], 0)
        return {
            'id': str(uuid.uuid4()), 'type': 'Mixed Parlay', 'legs': _cross_legs(sel),
            'num_games': len(sel), 'combined_odds': combined_odds, 'odds_range': '3.50-5.50',
            'confidence': _avg_conf(sel), 'generated_at': datetime.now().isoformat(),
        }

    def generate_big_odds(self) -> Dict:
        """Target odds 8.00-25.00, max 12 games."""
        pool = self._pool()
        res = engine.build_cross_game_ticket(pool, 8.00, 25.00, (5, 12), set())
        sel, combined_odds = res if res else ([], 0)
        return {
            'id': str(uuid.uuid4()), 'type': 'Big Odds', 'legs': _cross_legs(sel),
            'num_games': len(sel), 'combined_odds': combined_odds, 'odds_range': '8.00-25.00',
            'max_games': 12, 'confidence': _avg_conf(sel), 'generated_at': datetime.now().isoformat(),
        }

    def generate_mega_odds(self) -> Dict:
        """Target odds 27.00-50.00, max 15 games."""
        pool = self._pool()
        res = engine.build_cross_game_ticket(pool, 27.00, 50.00, (8, 15), set())
        sel, combined_odds = res if res else ([], 0)
        return {
            'id': str(uuid.uuid4()), 'type': 'Mega Odds', 'legs': _cross_legs(sel),
            'num_games': len(sel), 'combined_odds': combined_odds, 'odds_range': '27.00-50.00',
            'max_games': 15, 'confidence': _avg_conf(sel), 'generated_at': datetime.now().isoformat(),
        }

    def generate_all_daily_tickets(self) -> Dict:
        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'generated_at': datetime.now().isoformat(),
            'tickets': [
                self.generate_build_a_bet(),
                self.generate_mixed_parlay(),
                self.generate_big_odds(),
                self.generate_mega_odds(),
            ],
        }


_generator = None


def get_whatsapp_tickets_generator():
    global _generator
    if _generator is None:
        _generator = WhatsAppTicketsGenerator()
    return _generator
