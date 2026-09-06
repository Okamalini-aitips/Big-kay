"""Ticket Machine — engine-backed custom betslip builder.

Builds a custom ticket for a chosen odds range + market type. Every leg is a QUALIFYING tip
from the OkaMoney Betting Engine (user's 20 markets, all filters must pass). When a specific
market can't fill the requested odds, other qualifying markets are mixed in (flagged clearly).
See services/okamoney_engine.py and OKAMONEY_MARKET_SPEC_USER.md.
"""
import logging
import uuid
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from services import okamoney_engine as engine

logger = logging.getLogger(__name__)

ODDS_RANGES = {
    'safe': {'min': 1.80, 'max': 3.00, 'label': '1.80-3.00', 'typical_legs': (2, 3)},
    'value': {'min': 3.01, 'max': 7.00, 'label': '3.01-7.00', 'typical_legs': (2, 4)},
    'risky': {'min': 7.01, 'max': 12.00, 'label': '7.01-12.00', 'typical_legs': (3, 5)},
    'high_risk': {'min': 12.01, 'max': 20.00, 'label': '12.01-20.00', 'typical_legs': (4, 7)},
    'very_high': {'min': 20.01, 'max': 50.00, 'label': '20.01-50.00', 'typical_legs': (5, 10)},
    'extreme': {'min': 50.01, 'max': 99.00, 'label': '50.01-99.00', 'typical_legs': (7, 14)},
    'jackpot': {'min': 100.00, 'max': 500.00, 'label': '100+', 'typical_legs': (10, 20)},
}

MARKET_TYPES = {
    'all': {'label': 'All Markets'},
    'btts': {'label': 'BTTS'},
    'win': {'label': 'Win'},
    'dc_goals': {'label': 'DC and Goals'},
    'over25': {'label': 'Over 2.5 Goals'},
    'over15': {'label': 'Over 1.5 Goals'},
    'under35': {'label': 'Under 3.5 Goals'},
    'corners_1h': {'label': 'Over 4.5 1st Half Corners'},
    'cards': {'label': 'Over 3.5 Cards'},
}

# Market type -> engine market keys (primary, then optional fallback within same category)
MARKET_TYPE_KEYS = {
    'all': (None, None),
    'btts': ({'btts'}, None),
    'win': ({'straight_win'}, None),
    'dc_goals': ({'dc_over_1_5', 'dc_under_4_5'}, None),
    'over25': ({'over_2_5'}, None),
    'over15': ({'over_1_5'}, None),
    'under35': ({'under_3_5'}, None),
    'corners_1h': ({'over_4_5_fh_corners'}, {'over_8_5_corners', 'under_10_5_corners'}),
    'cards': ({'over_3_5_cards'}, {'over_2_5_cards', 'under_5_5_cards'}),
}

_ticket_machine = None


def get_ticket_machine():
    global _ticket_machine
    if _ticket_machine is None:
        _ticket_machine = TicketMachine()
    return _ticket_machine


class TicketMachine:
    def generate_ticket(self, odds_range: str, market_type: str) -> Dict:
        if odds_range not in ODDS_RANGES:
            raise ValueError(f"Invalid odds range: {odds_range}")
        if market_type not in MARKET_TYPES:
            raise ValueError(f"Invalid market type: {market_type}")

        rng_cfg = ODDS_RANGES[odds_range]
        legs_range = (max(2, rng_cfg['typical_legs'][0]), min(20, rng_cfg['typical_legs'][1]))
        pool = engine.get_daily_pool(70)
        primary, fallback = MARKET_TYPE_KEYS[market_type]

        markets_mixed = False
        mix_notice = None

        # 1) Try the requested market only
        res = engine.build_cross_game_ticket(pool, rng_cfg['min'], rng_cfg['max'], legs_range, set(), primary)
        # 2) Expand within the same category (corners/cards)
        if not res and fallback:
            keys = set(primary) | set(fallback)
            res = engine.build_cross_game_ticket(pool, rng_cfg['min'], rng_cfg['max'], legs_range, set(), keys)
            if res:
                markets_mixed = True
                mix_notice = f"Expanded to all {MARKET_TYPES[market_type]['label']} markets to reach target odds"
        # 3) Mix with all qualifying markets
        if not res and primary is not None:
            res = engine.build_cross_game_ticket(pool, rng_cfg['min'], rng_cfg['max'],
                                                 (legs_range[0], 20), set(), None)
            if res:
                markets_mixed = True
                mix_notice = f"Mixed with other markets — not enough {MARKET_TYPES[market_type]['label']} games to meet odds target"
        # 4) Last resort: widen legs for 'all'
        if not res:
            res = engine.build_cross_game_ticket(pool, rng_cfg['min'], rng_cfg['max'], (2, 20), set(), None)

        if not res:
            # Could not hit the bracket exactly — return closest high-probability selection
            ticket = self._closest_ticket(pool, rng_cfg, primary)
            markets_mixed = True
            mix_notice = "Could not match the exact odds target with qualifying tips only"
        else:
            sel, combined_odds = res
            ticket = self._ticket_from_selection(sel, combined_odds)

        ticket['id'] = str(uuid.uuid4())
        ticket['odds_range'] = rng_cfg['label']
        ticket['market_type'] = MARKET_TYPES[market_type]['label']
        ticket['original_market'] = MARKET_TYPES[market_type]['label']
        ticket['markets_mixed'] = markets_mixed
        ticket['generated_at'] = datetime.utcnow().isoformat()
        if markets_mixed and mix_notice:
            ticket['mix_notice'] = mix_notice
        return ticket

    def _ticket_from_selection(self, sel: List[Dict], combined_odds: float) -> Dict:
        legs = []
        for item in sel:
            g, t = item['game'], item['tip']
            legs.append({
                'home': g['home'], 'away': g['away'], 'league': g['league'],
                'market': t['market'], 'selection': t['selection'],
                'odds': t['odds'], 'probability': t['probability'], 'confidence': t['confidence'],
            })
        return self._finalize(legs, combined_odds)

    def _closest_ticket(self, pool, rng_cfg, primary) -> Dict:
        # Take best qualifying tips (respecting market if possible) until near the target
        target = (rng_cfg['min'] + rng_cfg['max']) / 2
        items = []
        for g in pool:
            t = engine.best_tip(g, primary)
            if t:
                items.append((g, t))
        items.sort(key=lambda x: x[1]['probability'], reverse=True)
        legs, combined = [], 1.0
        for g, t in items:
            legs.append({'home': g['home'], 'away': g['away'], 'league': g['league'],
                         'market': t['market'], 'selection': t['selection'],
                         'odds': t['odds'], 'probability': t['probability'], 'confidence': t['confidence']})
            combined *= t['odds']
            if combined >= target or len(legs) >= 20:
                break
        return self._finalize(legs, round(combined, 2))

    def _finalize(self, legs: List[Dict], combined_odds: float) -> Dict:
        n = max(len(legs), 1)
        avg_prob = sum(l['probability'] for l in legs) / n
        adjusted = avg_prob * (0.96 ** (n - 1))
        conf = 'High' if adjusted >= 65 else ('Medium' if adjusted >= 50 else 'Low')
        return {
            'legs': legs,
            'num_legs': len(legs),
            'combined_odds': round(combined_odds, 2),
            'combined_probability': round(adjusted, 1),
            'confidence': conf,
        }


def get_odds_ranges() -> Dict:
    return {k: {'label': v['label'], 'typical_legs': v['typical_legs']} for k, v in ODDS_RANGES.items()}


def get_market_types() -> Dict:
    return {k: {'label': v['label']} for k, v in MARKET_TYPES.items()}
