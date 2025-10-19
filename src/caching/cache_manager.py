"""
Cache manager for the Kindle Sync application.

Provides a unified interface for caching with support for multiple backends.
"""

import asyncio
import hashlib
import json
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional, Union

from loguru import logger
from pathlib import Path

from .memory_cache import MemoryCache
from .redis_cache import RedisCache


class CacheBackend(ABC):
    """Abstract base class for cache backends."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in the cache."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a value from the cache."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """Clear all values from the cache."""
        pass

    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        pass


class CacheManager:
    """Manages caching operations with support for multiple backends."""

    def __init__(self, backend: Optional[CacheBackend] = None, default_ttl: int = 3600):
        """
        Initialize cache manager.

        Args:
            backend: Cache backend to use (defaults to MemoryCache)
            default_ttl: Default time-to-live in seconds
        """
        self.backend = backend or MemoryCache()
        self.default_ttl = default_ttl
        self.key_prefix = "kindle_sync:"

    def _make_key(self, key: str) -> str:
        """Create a prefixed cache key."""
        return f"{self.key_prefix}{key}"

    def _serialize_value(self, value: Any) -> str:
        """Serialize a value for storage."""
        try:
            return json.dumps(value, default=str)
        except (TypeError, ValueError) as e:
            logger.warning(f"Failed to serialize value: {e}")
            return str(value)

    def _deserialize_value(self, value: str) -> Any:
        """Deserialize a value from storage."""
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return value

    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        try:
            cache_key = self._make_key(key)
            value = await self.backend.get(cache_key)

            if value is not None:
                return self._deserialize_value(value)

            return None

        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)

        Returns:
            True if successful, False otherwise
        """
        try:
            cache_key = self._make_key(key)
            serialized_value = self._serialize_value(value)
            ttl = ttl or self.default_ttl

            return await self.backend.set(cache_key, serialized_value, ttl)

        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
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
            cache_key = self._make_key(key)
            return await self.backend.delete(cache_key)

        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
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
            cache_key = self._make_key(key)
            return await self.backend.exists(cache_key)

        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False

    async def clear(self) -> bool:
        """
        Clear all values from the cache.

        Returns:
            True if successful, False otherwise
        """
        try:
            return await self.backend.clear()

        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False

    async def get_or_set(
        self, key: str, factory: Callable, ttl: Optional[int] = None
    ) -> Any:
        """
        Get a value from cache or set it using a factory function.

        Args:
            key: Cache key
            factory: Function to call if value not in cache
            ttl: Time-to-live in seconds

        Returns:
            Cached or newly created value
        """
        # Try to get from cache first
        value = await self.get(key)
        if value is not None:
            return value

        # Generate new value using factory
        try:
            if asyncio.iscoroutinefunction(factory):
                value = await factory()
            else:
                value = factory()

            # Cache the new value
            await self.set(key, value, ttl)
            return value

        except Exception as e:
            logger.error(f"Cache get_or_set error for key {key}: {e}")
            raise

    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all keys matching a pattern.

        Args:
            pattern: Pattern to match (supports * wildcard)

        Returns:
            Number of keys invalidated
        """
        # This is a simplified implementation
        # In a real Redis implementation, you'd use SCAN with MATCH
        logger.warning("Pattern invalidation not fully implemented for this backend")
        return 0

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary of cache statistics
        """
        try:
            stats = await self.backend.get_stats()
            stats["backend_type"] = type(self.backend).__name__
            stats["default_ttl"] = self.default_ttl
            return stats

        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {"error": str(e)}

    def create_key(self, *parts: Union[str, int, float]) -> str:
        """
        Create a cache key from multiple parts.

        Args:
            *parts: Parts to combine into a key

        Returns:
            Combined cache key
        """
        key_parts = [str(part) for part in parts]
        return ":".join(key_parts)

    def create_hash_key(self, *parts: Union[str, int, float]) -> str:
        """
        Create a hash-based cache key from multiple parts.

        Args:
            *parts: Parts to hash into a key

        Returns:
            Hashed cache key
        """
        key_string = ":".join(str(part) for part in parts)
        return hashlib.md5(key_string.encode()).hexdigest()


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def initialize_cache_manager(
    backend: Optional[CacheBackend] = None, default_ttl: int = 3600
) -> CacheManager:
    """
    Initialize global cache manager.

    Args:
        backend: Cache backend to use
        default_ttl: Default time-to-live in seconds

    Returns:
        Initialized cache manager
    """
    global _cache_manager
    _cache_manager = CacheManager(backend, default_ttl)
    return _cache_manager


def get_cache_manager() -> Optional[CacheManager]:
    """
    Get the global cache manager instance.

    Returns:
        Cache manager instance or None if not initialized
    """
    global _cache_manager
    return _cache_manager


def get_cache() -> CacheManager:
    """
    Get the global cache manager, initializing with default backend if needed.

    Returns:
        Cache manager instance
    """
    global _cache_manager

    if _cache_manager is None:
        _cache_manager = CacheManager()

    return _cache_manager
