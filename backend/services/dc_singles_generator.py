"""Double Chance Singles Generator — engine-backed.

Produces DC & Under 4.5 and DC & Over 1.5 single-bet cards, sourced from the OkaMoney
Betting Engine (markets 14 and 13; all filters must pass). See services/okamoney_engine.py.
"""
import logging
import uuid
from typing import List, Dict, Optional

from services import okamoney_engine as engine

logger = logging.getLogger(__name__)


def _card(g: Dict, tip: Dict, kind: str) -> Dict:
    combined_odds = tip['odds']
    dc_sel = tip['selection'].split(' & ')[0]
    dc_odds = round(min(1.45, max(1.15, combined_odds * 0.8)), 2)
    leg_odds = round(max(1.05, combined_odds / dc_odds), 2)
    conf = round(tip['probability'] / 100, 2)
    card = {
        'id': str(uuid.uuid4()),
        'type': f'DC & {kind}',
        'market': f"Double Chance & {'Under 4.5 Goals' if kind == 'Under 4.5' else 'Over 1.5 Goals'}",
        'match': {'home': g['home'], 'away': g['away'], 'league': g['league'],
                  'date': g['date'], 'fixture_id': g['fixture_id']},
        'dc_selection': dc_sel, 'dc_odds': dc_odds, 'dc_confidence': conf,
        'combined_odds': combined_odds, 'combined_confidence': round(tip['probability']),
        'home_form': g['home_form'], 'away_form': g['away_form'], 'h2h': g['h2h'],
    }
    if kind == 'Under 4.5':
        card.update({'under_selection': 'Under 4.5', 'under_odds': leg_odds, 'under_confidence': conf})
    else:
        card.update({'over_selection': 'Over 1.5', 'over_odds': leg_odds, 'over_confidence': conf})
    return card


class DCSinglesGenerator:
    def generate_dc_under_singles(self, target_date: Optional[str] = None) -> List[Dict]:
        pool = engine.get_daily_pool(70)
        cards = []
        for g in pool:
            tip = engine.best_tip(g, {'dc_under_4_5'})
            if tip:
                cards.append(_card(g, tip, 'Under 4.5'))
        cards.sort(key=lambda x: x['combined_confidence'], reverse=True)
        return cards[:4]

    def generate_dc_over_singles(self, target_date: Optional[str] = None) -> List[Dict]:
        pool = engine.get_daily_pool(70)
        cards = []
        for g in pool:
            tip = engine.best_tip(g, {'dc_over_1_5'})
            if tip:
                cards.append(_card(g, tip, 'Over 1.5'))
        cards.sort(key=lambda x: x['combined_confidence'], reverse=True)
        return cards[:4]


_dc_singles_generator = None


def get_dc_singles_generator() -> DCSinglesGenerator:
    global _dc_singles_generator
    if _dc_singles_generator is None:
        _dc_singles_generator = DCSinglesGenerator()
    return _dc_singles_generator
