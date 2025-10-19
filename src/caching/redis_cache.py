"""
Redis cache implementation for the Kindle Sync application.

Provides Redis-based caching with TTL support.
"""

from typing import Any

from loguru import logger

try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None


class RedisCache:
    """Redis-based cache implementation."""

    def __init__(self, config: dict | None = None):
        """
        Initialize Redis cache.

        Args:
            config: Redis configuration dictionary
        """
        if not REDIS_AVAILABLE:
            raise ImportError("Redis is not available. Install redis package.")

        self.config = config or {}
        self.redis_client = None
        self._stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0, "errors": 0}

    async def connect(self):
        """Connect to Redis server."""
        try:
            self.redis_client = redis.Redis(
                host=self.config.get("host", "localhost"),
                port=self.config.get("port", 6379),
                db=self.config.get("db", 0),
                password=self.config.get("password"),
                decode_responses=True,
            )

            # Test connection
            await self.redis_client.ping()
            logger.info("Connected to Redis server")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self):
        """Disconnect from Redis server."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Disconnected from Redis server")

    async def get(self, key: str) -> Any | None:
        """
        Get a value from the cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        try:
            if not self.redis_client:
                await self.connect()

            value = await self.redis_client.get(key)

            if value is not None:
                self._stats["hits"] += 1
                return value
            else:
                self._stats["misses"] += 1
                return None

        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"Redis get error for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """
        Set a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.redis_client:
                await self.connect()

            if ttl:
                await self.redis_client.setex(key, ttl, value)
            else:
                await self.redis_client.set(key, value)

            self._stats["sets"] += 1
            return True

        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"Redis set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.

        Args:
            key: Cache key

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.redis_client:
                await self.connect()

            result = await self.redis_client.delete(key)
            self._stats["deletes"] += 1
            return bool(result)

        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"Redis delete error for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache.

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise
        """
        try:
            if not self.redis_client:
                await self.connect()

            result = await self.redis_client.exists(key)
            return bool(result)

        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"Redis exists error for key {key}: {e}")
            return False

    async def clear(self) -> bool:
        """
        Clear all values from the cache.

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.redis_client:
                await self.connect()

            await self.redis_client.flushdb()
            return True

        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"Redis clear error: {e}")
            return False

    async def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary of cache statistics
        """
        try:
            if not self.redis_client:
                await self.connect()

            # Get Redis info
            info = await self.redis_client.info()

            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = (
                (self._stats["hits"] / total_requests * 100)
                if total_requests > 0
                else 0
            )

            return {
                "redis_info": {
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory": info.get("used_memory", 0),
                    "used_memory_human": info.get("used_memory_human", "0B"),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0),
                },
                "cache_stats": {
                    "hits": self._stats["hits"],
                    "misses": self._stats["misses"],
                    "hit_rate": round(hit_rate, 2),
                    "sets": self._stats["sets"],
                    "deletes": self._stats["deletes"],
                    "errors": self._stats["errors"],
                },
            }

        except Exception as e:
            logger.error(f"Redis stats error: {e}")
            return {"error": str(e)}
