"""
ET InvestorIQ — Cache Service
Wraps fakeredis (fallback from real Redis). Provides simple get/set/delete/exists API.
Cache TTLs: stock prices=5min, fundamentals=1hr, news=15min, signals=30min,
            bulk deals=1hr, FII data=4hr.
"""

import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Cache TTL constants (seconds)
TTL_STOCK_PRICES = 300       # 5 minutes
TTL_FUNDAMENTALS = 3600      # 1 hour
TTL_NEWS = 900               # 15 minutes
TTL_SIGNALS = 1800           # 30 minutes
TTL_BULK_DEALS = 3600        # 1 hour
TTL_FII_DATA = 14400         # 4 hours
TTL_SECTOR = 1800            # 30 minutes


class CacheService:
    """
    Unified cache service backed by Redis (or fakeredis for offline mode).
    Falls back gracefully to an in-memory dict if Redis is unavailable.
    """

    def __init__(self):
        """Initialize cache connection — prefers real Redis, falls back to fakeredis."""
        self._client = None
        self._memory_cache: dict = {}  # Last-resort in-memory fallback
        self._use_memory = False
        self._init_client()

    def _init_client(self):
        """Attempt to connect to Redis; fall back to fakeredis or memory."""
        from app.config import settings
        try:
            import redis
            r = redis.from_url(settings.redis_url, socket_connect_timeout=2)
            r.ping()
            self._client = r
            logger.info("Connected to Redis at %s", settings.redis_url)
        except Exception as e:
            logger.warning(f"Redis unavailable ({e}). Falling back to fakeredis.")
            try:
                import fakeredis
                self._client = fakeredis.FakeRedis()
                logger.info("Using fakeredis (in-process mock Redis).")
            except Exception as fe:
                logger.warning(f"fakeredis unavailable ({fe}). Using in-memory dict fallback.")
                self._use_memory = True

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a cached value.

        Args:
            key: Cache key.

        Returns:
            Deserialized value, or None if not found / expired.
        """
        try:
            if self._use_memory:
                return self._memory_cache.get(key)
            raw = self._client.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as e:
            logger.warning(f"Cache get failed for {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> bool:
        """
        Store a value in cache with TTL.

        Args:
            key: Cache key.
            value: Value to serialize and store.
            ttl_seconds: Time-to-live in seconds.

        Returns:
            True if stored successfully, False otherwise.
        """
        try:
            if self._use_memory:
                self._memory_cache[key] = value
                return True
            serialized = json.dumps(value, default=str)
            self._client.setex(key, ttl_seconds, serialized)
            return True
        except Exception as e:
            logger.warning(f"Cache set failed for {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete a key from cache.

        Args:
            key: Cache key to delete.

        Returns:
            True if deleted, False if key didn't exist or error.
        """
        try:
            if self._use_memory:
                self._memory_cache.pop(key, None)
                return True
            self._client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete failed for {key}: {e}")
            return False

    def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache.

        Args:
            key: Cache key.

        Returns:
            True if key exists and not expired.
        """
        try:
            if self._use_memory:
                return key in self._memory_cache
            return bool(self._client.exists(key))
        except Exception as e:
            logger.warning(f"Cache exists check failed for {key}: {e}")
            return False

    def flush(self) -> bool:
        """Clear all cache keys. Use with caution."""
        try:
            if self._use_memory:
                self._memory_cache.clear()
                return True
            self._client.flushall()
            return True
        except Exception as e:
            logger.warning(f"Cache flush failed: {e}")
            return False

    # ─── Convenience helpers with built-in TTLs ───────────────────────────────

    def cache_stock_prices(self, symbol: str, data: Any) -> bool:
        """Cache stock price data for 5 minutes."""
        return self.set(f"prices:{symbol}", data, TTL_STOCK_PRICES)

    def get_stock_prices(self, symbol: str) -> Optional[Any]:
        """Get cached stock price data."""
        return self.get(f"prices:{symbol}")

    def cache_fundamentals(self, symbol: str, data: Any) -> bool:
        """Cache fundamentals for 1 hour."""
        return self.set(f"fundamentals:{symbol}", data, TTL_FUNDAMENTALS)

    def get_fundamentals(self, symbol: str) -> Optional[Any]:
        """Get cached fundamentals."""
        return self.get(f"fundamentals:{symbol}")

    def cache_news(self, symbol: str, data: Any) -> bool:
        """Cache news for 15 minutes."""
        return self.set(f"news:{symbol}", data, TTL_NEWS)

    def get_news(self, symbol: str) -> Optional[Any]:
        """Get cached news."""
        return self.get(f"news:{symbol}")

    def cache_signals(self, data: Any) -> bool:
        """Cache radar signals for 30 minutes."""
        return self.set("signals:latest", data, TTL_SIGNALS)

    def get_signals(self) -> Optional[Any]:
        """Get cached signals."""
        return self.get("signals:latest")

    def cache_bulk_deals(self, data: Any) -> bool:
        """Cache bulk deals for 1 hour."""
        return self.set("bulk_deals:latest", data, TTL_BULK_DEALS)

    def get_bulk_deals(self) -> Optional[Any]:
        """Get cached bulk deals."""
        return self.get("bulk_deals:latest")

    def cache_fii_data(self, data: Any) -> bool:
        """Cache FII/DII data for 4 hours."""
        return self.set("fii_data:latest", data, TTL_FII_DATA)

    def get_fii_data(self) -> Optional[Any]:
        """Get cached FII/DII data."""
        return self.get("fii_data:latest")


# Singleton instance
cache = CacheService()
