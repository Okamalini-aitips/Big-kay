"""Daily Games Generator for OkaMoney AI Tips.

Every tip is produced by the OkaMoney Betting Engine (the user's 20 markets, exact
filters, all-filters-must-pass, ranked by blended probability). While API-Sports is
inactive the engine runs on realistic synthetic data; when live data returns the same
engine runs on real fixtures. See services/okamoney_engine.py and OKAMONEY_MARKET_SPEC_USER.md.
"""
import logging
import uuid
from typing import List, Dict, Optional
from datetime import datetime

from services.api_football import APIFootballService
from services import okamoney_engine as engine

logger = logging.getLogger(__name__)

TARGET_LEAGUE_IDS = {
    39: "Premier League", 140: "La Liga", 135: "Serie A", 78: "Bundesliga", 61: "Ligue 1",
    88: "Eredivisie", 94: "Primeira Liga", 144: "Belgian Pro League",
    40: "Championship", 79: "Bundesliga 2", 141: "La Liga 2", 136: "Serie B", 62: "Ligue 2",
    179: "Scottish Premiership", 203: "Süper Lig", 2: "UEFA Champions League",
    3: "UEFA Europa League", 848: "UEFA Conference League",
}

_games_generator = None


def get_games_generator():
    global _games_generator
    if _games_generator is None:
        _games_generator = GamesGenerator()
    return _games_generator


def _markets_from_tips(tips: List[Dict]) -> List[Dict]:
    return [{
        'market': t['market'],
        'selection': t['selection'],
        'probability': t['probability'],
        'confidence': t['confidence'],
        'odds': t['odds'],
        'filters_passed': t['filters_passed'],
        'total_filters': t['total_filters'],
    } for t in tips]


def _game_from_engine(g: Dict) -> Dict:
    tips = g['tips'][:2]  # daily tips: max 2 per game
    combined = round(sum(t['probability'] for t in tips) / len(tips), 1) if tips else g['combined_probability']
    return {
        'id': g['id'],
        'fixture_id': g['fixture_id'],
        'match': {'home': g['home'], 'away': g['away'], 'league': g['league'], 'date': g['date']},
        'markets': _markets_from_tips(tips),
        'combined_probability': combined,
        'home_form': g['home_form'],
        'away_form': g['away_form'],
        'is_free': False,
        'rank': 0,
    }


class GamesGenerator:
    """Generate daily games, each with up to 3 qualifying tips from the engine."""

    def __init__(self):
        self.api = APIFootballService()

    def generate_daily_games(self, target_date: Optional[str] = None, limit: int = 100) -> List[Dict]:
        if target_date is None:
            target_date = datetime.now().strftime('%Y-%m-%d')
        logger.info(f"🎯 Generating daily games for {target_date}")

        games: List[Dict] = []

        # Live-data path (runs the SAME engine on real fixtures when available)
        try:
            if hasattr(self.api, 'get_fixtures_by_date'):
                for league_id in TARGET_LEAGUE_IDS.keys():
                    for fixture in (self.api.get_fixtures_by_date(target_date, league_id) or []):
                        game = self._analyze_real_fixture(fixture)
                        if game:
                            games.append(game)
        except Exception as e:
            logger.error(f"Error fetching/analyzing live fixtures: {e}")

        # Supplement (or fully populate while API is inactive) from the engine pool
        if len(games) < limit:
            pool = engine.get_daily_pool(max(limit, 70))
            for g in pool:
                games.append(_game_from_engine(g))

        games.sort(key=lambda x: x.get('combined_probability', 0), reverse=True)
        games = games[:limit]
        for i, game in enumerate(games):
            game['is_free'] = i < 3
            game['rank'] = i + 1
        return games

    def _analyze_real_fixture(self, fixture: Dict) -> Optional[Dict]:
        try:
            league_id = fixture['league']['id']
            season = fixture['league']['season']
            home_id = fixture['teams']['home']['id']
            away_id = fixture['teams']['away']['id']
            home_name = fixture['teams']['home']['name']
            away_name = fixture['teams']['away']['name']

            home_stats = self.api.get_team_statistics(home_id, league_id, season)
            away_stats = self.api.get_team_statistics(away_id, league_id, season)
            if not home_stats or not away_stats:
                return None

            home_raw = self._extract_stats(home_stats); home_raw['name'] = home_name
            away_raw = self._extract_stats(away_stats); away_raw['name'] = away_name
            odds = self._extract_odds(self.api.get_odds(fixture['fixture']['id'], bet_id=1))
            h2h = self.api.get_h2h(home_id, away_id, last=5)

            tips = engine.evaluate_fixture(home_raw, away_raw, odds, h2h, league_id)
            if not tips:
                return None
            markets = _markets_from_tips(tips[:2])
            combined = round(sum(m['probability'] for m in markets) / len(markets), 1)
            return {
                'id': str(uuid.uuid4()),
                'fixture_id': fixture['fixture']['id'],
                'match': {'home': home_name, 'away': away_name,
                          'league': fixture['league']['name'], 'date': fixture['fixture']['date']},
                'markets': markets,
                'combined_probability': combined,
                'home_form': 'N/A', 'away_form': 'N/A',
                'is_free': False, 'rank': 0,
            }
        except Exception as e:
            logger.error(f"Error analyzing fixture: {e}")
            return None

    def _extract_odds(self, odds_data) -> Dict:
        if not odds_data:
            return {}
        try:
            for bookmaker in odds_data.get('bookmakers', []):
                for bet in bookmaker.get('bets', []):
                    if bet.get('name') == 'Match Winner':
                        v = {x['value']: x['odd'] for x in bet.get('values', [])}
                        return {'home_win': float(v.get('Home', 0)), 'draw': float(v.get('Draw', 0)),
                                'away_win': float(v.get('Away', 0))}
        except Exception:
            pass
        return {}

    def _extract_stats(self, stats) -> Dict:
        try:
            fixtures = stats.get('fixtures', {})
            goals = stats.get('goals', {})
            played = fixtures.get('played', {}).get('total', 10) or 10
            return {
                'played': played,
                'wins': fixtures.get('wins', {}).get('total', 4),
                'draws': fixtures.get('draws', {}).get('total', 3),
                'goals_avg': goals.get('for', {}).get('average', {}).get('total', 1.3),
                'conceded_avg': goals.get('against', {}).get('average', {}).get('total', 1.2),
                'clean_sheets': stats.get('clean_sheet', {}).get('total', 3),
                'failed_to_score': stats.get('failed_to_score', {}).get('total', 2),
            }
        except Exception:
            return {'played': 10, 'wins': 4, 'draws': 3, 'goals_avg': 1.4, 'conceded_avg': 1.2,
                    'clean_sheets': 3, 'failed_to_score': 2}
