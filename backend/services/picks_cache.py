"""Picks cache manager - Generate once, serve fast"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
from services.pick_generator import PickGenerator

logger = logging.getLogger(__name__)

class PicksCache:
    """Cache manager for daily picks"""
    
    def __init__(self):
        self._cache = None
        self._cache_time = None
        self._cache_ttl_hours = 6  # Regenerate every 6 hours
        self._generator = None
        
    def get_generator(self):
        """Get or create pick generator"""
        if self._generator is None:
            self._generator = PickGenerator()
        return self._generator
        
    def is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        if self._cache is None or self._cache_time is None:
            return False
            
        age = datetime.utcnow() - self._cache_time
        return age.total_seconds() < (self._cache_ttl_hours * 3600)
        
    def get_picks(self, force_refresh: bool = False) -> List[Dict]:
        """Get picks from cache or generate new ones"""
        
        if force_refresh or not self.is_cache_valid():
            logger.info("Cache invalid or refresh requested - generating new picks...")
            try:
                generator = self.get_generator()
                # Analyze up to 100 matches to get more DC U/4.5 picks
                # PRO plan allows plenty of API calls
                picks = generator.generate_daily_picks(hours_ahead=24, max_matches=100)
                
                self._cache = picks
                self._cache_time = datetime.utcnow()
                
                logger.info(f"✅ Generated and cached {len(picks)} picks")
                return picks
                
            except Exception as e:
                logger.error(f"Error generating picks: {e}")
                # Return empty or old cache
                if self._cache:
                    logger.warning("Returning old cache due to error")
                    return self._cache
                return []
        else:
            # Serve from cache
            cache_age = datetime.utcnow() - self._cache_time
            logger.info(f"✅ Serving {len(self._cache)} picks from cache (age: {cache_age.total_seconds()/60:.1f} min)")
            return self._cache
            
    def get_cache_info(self) -> Dict:
        """Get cache status info"""
        if self._cache is None:
            return {
                "cached": False,
                "picks_count": 0,
                "cache_age_minutes": 0,
                "cache_valid": False
            }
            
        age = datetime.utcnow() - self._cache_time if self._cache_time else timedelta(0)
        
        return {
            "cached": True,
            "picks_count": len(self._cache),
            "cache_age_minutes": age.total_seconds() / 60,
            "cache_valid": self.is_cache_valid(),
            "cache_time": self._cache_time.isoformat() if self._cache_time else None,
            "next_refresh": (self._cache_time + timedelta(hours=self._cache_ttl_hours)).isoformat() if self._cache_time else None
        }

# Global cache instance
_picks_cache = PicksCache()

def get_picks_cache() -> PicksCache:
    """Get global picks cache instance"""
    return _picks_cache

def clear_cache():
    """Clear the global picks cache to force regeneration"""
    global _picks_cache
    _picks_cache._cache = None
    _picks_cache._cache_time = None
    logger.info("✅ Picks cache cleared")
