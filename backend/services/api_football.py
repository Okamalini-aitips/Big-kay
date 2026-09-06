"""API-Football (API-SPORTS) integration service with caching"""
import requests
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import time

logger = logging.getLogger(__name__)

class APIFootballService:
    """Service to interact with API-Football (api-sports.io)"""
    
    def __init__(self):
        self.api_key = os.getenv('API_FOOTBALL_KEY')
        self.api_host = os.getenv('API_FOOTBALL_HOST', 'v3.football.api-sports.io')
        self.base_url = f'https://{self.api_host}'
        self.headers = {
            'x-apisports-key': self.api_key
        }
        self._cache = {}
        self._cache_ttl = {}
        self._last_request_time = 0
        self._request_count = 0
        self._rate_limit_window = 60  # 1 minute
        self._max_requests_per_minute = 28  # PRO plan allows more - stay under 30/min for safety
        
    def _respect_rate_limit(self):
        """Ensure we don't exceed rate limits"""
        current_time = time.time()
        
        # Reset counter if window passed
        if current_time - self._last_request_time >= self._rate_limit_window:
            self._request_count = 0
            self._last_request_time = current_time
            
        # If we hit the limit, wait
        if self._request_count >= self._max_requests_per_minute:
            wait_time = self._rate_limit_window - (current_time - self._last_request_time)
            if wait_time > 0:
                logger.info(f"⏳ Rate limit reached. Waiting {wait_time:.1f}s...")
                time.sleep(wait_time + 1)
                self._request_count = 0
                self._last_request_time = time.time()
                
        self._request_count += 1
        
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make API request with error handling"""
        try:
            self._respect_rate_limit()
            
            url = f"{self.base_url}/{endpoint}"
            logger.info(f"API Request: {endpoint} with params: {params}")
            
            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                timeout=10
            )
            
            response.raise_for_status()
            data = response.json()
            
            if data.get('errors') and len(data.get('errors', {})) > 0:
                logger.error(f"API Error: {data['errors']}")
                return None
                
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None
            
    def _get_cached(self, key: str, ttl_hours: int = 24) -> Optional[any]:
        """Get cached data if still valid"""
        if key in self._cache:
            if key in self._cache_ttl:
                if datetime.utcnow() < self._cache_ttl[key]:
                    logger.info(f"Cache hit: {key}")
                    return self._cache[key]
        return None
        
    def _set_cache(self, key: str, data: any, ttl_hours: int = 24):
        """Set cache with TTL"""
        self._cache[key] = data
        self._cache_ttl[key] = datetime.utcnow() + timedelta(hours=ttl_hours)
        
    def get_fixtures(self, date: str = None, league_ids: List[int] = None, next_n: int = 50) -> List[Dict]:
        """Get fixtures for a specific date or upcoming fixtures
        
        Args:
            date: Date in YYYY-MM-DD format (default: today)
            league_ids: List of league IDs to filter (optional)
            next_n: Number of upcoming fixtures to fetch
            
        Returns:
            List of fixture dictionaries
        """
        if not date:
            date = datetime.utcnow().strftime('%Y-%m-%d')
            
        cache_key = f"fixtures_{date}"
        cached = self._get_cached(cache_key, ttl_hours=6)
        if cached:
            return cached
            
        params = {'date': date}
        
        data = self._make_request('fixtures', params)
        
        if data and 'response' in data:
            fixtures = data['response']
            self._set_cache(cache_key, fixtures, ttl_hours=6)
            return fixtures
            
        return []
    
    def get_fixtures_range(self, date_from: str, date_to: str) -> List[Dict]:
        """Get fixtures in a date range"""
        # API-SPORTS requires either 'date' or 'from'+'to' with timezone
        # For simplicity, get both days separately
        fixtures = []
        
        from datetime import datetime, timedelta
        start = datetime.strptime(date_from, '%Y-%m-%d')
        end = datetime.strptime(date_to, '%Y-%m-%d')
        
        current = start
        while current <= end:
            date_str = current.strftime('%Y-%m-%d')
            daily_fixtures = self.get_fixtures(date=date_str)
            fixtures.extend(daily_fixtures)
            current += timedelta(days=1)
            
        return fixtures
        
    def get_odds(self, fixture_id: int, bet_id: int = 1) -> Optional[Dict]:
        """Get odds for a specific fixture
        
        Args:
            fixture_id: The fixture ID
            bet_id: Bet type ID (1=Match Winner, 5=Goals O/U, etc.)
            
        Returns:
            Odds data dictionary
        """
        cache_key = f"odds_{fixture_id}_{bet_id}"
        cached = self._get_cached(cache_key, ttl_hours=2)
        if cached:
            return cached
            
        params = {
            'fixture': fixture_id,
            'bet': bet_id
        }
        
        data = self._make_request('odds', params)
        
        if data and 'response' in data and len(data['response']) > 0:
            odds_data = data['response'][0]
            self._set_cache(cache_key, odds_data, ttl_hours=2)
            return odds_data
            
        return None
        
    def get_team_statistics(self, team_id: int, league_id: int, season: int = None) -> Optional[Dict]:
        """Get team statistics for a league/season
        
        Args:
            team_id: Team ID
            league_id: League ID  
            season: Season year (e.g., 2024) - Free plan: 2022-2024 only
            
        Returns:
            Team statistics dictionary
        """
        # Free plan limitation: only 2022-2024 available
        if not season or season > 2024:
            season = 2024  # Use latest available season for free plan
            
        cache_key = f"team_stats_{team_id}_{league_id}_{season}"
        cached = self._get_cached(cache_key, ttl_hours=24)
        if cached:
            return cached
            
        params = {
            'team': team_id,
            'league': league_id,
            'season': season
        }
        
        data = self._make_request('teams/statistics', params)
        
        if data and 'response' in data:
            stats = data['response']
            self._set_cache(cache_key, stats, ttl_hours=24)
            return stats
            
        return None
        
    def get_h2h(self, team1_id: int, team2_id: int, last: int = 5) -> List[Dict]:
        """Get head-to-head matches between two teams
        
        Args:
            team1_id: First team ID
            team2_id: Second team ID
            last: Number of recent H2H matches
            
        Returns:
            List of H2H match dictionaries
        """
        cache_key = f"h2h_{team1_id}_{team2_id}_{last}"
        cached = self._get_cached(cache_key, ttl_hours=48)
        if cached:
            return cached
            
        params = {
            'h2h': f"{team1_id}-{team2_id}",
            'last': last
        }
        
        data = self._make_request('fixtures/headtohead', params)
        
        if data and 'response' in data:
            h2h_matches = data['response']
            self._set_cache(cache_key, h2h_matches, ttl_hours=48)
            return h2h_matches
            
        return []
        
    def test_connection(self) -> bool:
        """Test API connection and key validity"""
        try:
            data = self._make_request('status')
            if data and 'response' in data:
                logger.info(f"API Connection successful: {data['response']}")
                return True
            return False
        except Exception as e:
            logger.error(f"API Connection failed: {e}")
            return False
