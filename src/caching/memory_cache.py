"""
In-memory cache implementation for the Kindle Sync application.

Provides a simple in-memory cache with TTL support.
"""

import time
import asyncio
from typing import Any, Optional, Dict
from collections import OrderedDict
from threading import RLock
from loguru import logger


class MemoryCache:
    """In-memory cache with TTL support and LRU eviction."""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """
        Initialize memory cache.
        
        Args:
            max_size: Maximum number of items to store
            default_ttl: Default time-to-live in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._lock = RLock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "evictions": 0
        }
    
    def _is_expired(self, item: Dict[str, Any]) -> bool:
        """Check if a cache item has expired."""
        return time.time() > item["expires_at"]
    
    def _cleanup_expired(self):
        """Remove expired items from the cache."""
        current_time = time.time()
        expired_keys = []
        
        for key, item in self._cache.items():
            if current_time > item["expires_at"]:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
            self._stats["evictions"] += 1
    
    def _evict_lru(self):
        """Evict the least recently used item."""
        if self._cache:
            key, _ = self._cache.popitem(last=False)
            self._stats["evictions"] += 1
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            if key not in self._cache:
                self._stats["misses"] += 1
                return None
            
            item = self._cache[key]
            
            # Check if expired
            if self._is_expired(item):
                del self._cache[key]
                self._stats["misses"] += 1
                self._stats["evictions"] += 1
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._stats["hits"] += 1
            
            return item["value"]
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds
            
        Returns:
            True if successful
        """
        try:
            with self._lock:
                # Clean up expired items first
                self._cleanup_expired()
                
                # Calculate expiration time
                expires_at = time.time() + (ttl or self.default_ttl)
                
                # Remove existing key if present
                if key in self._cache:
                    del self._cache[key]
                
                # Add new item
                self._cache[key] = {
                    "value": value,
                    "expires_at": expires_at,
                    "created_at": time.time()
                }
                
                # Evict LRU if over capacity
                while len(self._cache) > self.max_size:
                    self._evict_lru()
                
                self._stats["sets"] += 1
                return True
                
        except Exception as e:
            logger.error(f"Memory cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key was deleted, False if not found
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats["deletes"] += 1
                return True
            
            return False
    
    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists and is not expired
        """
        with self._lock:
            if key not in self._cache:
                return False
            
            item = self._cache[key]
            
            # Check if expired
            if self._is_expired(item):
                del self._cache[key]
                self._stats["evictions"] += 1
                return False
            
            return True
    
    async def clear(self) -> bool:
        """
        Clear all values from the cache.
        
        Returns:
            True if successful
        """
        try:
            with self._lock:
                self._cache.clear()
                return True
                
        except Exception as e:
            logger.error(f"Memory cache clear error: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary of cache statistics
        """
        with self._lock:
            # Clean up expired items for accurate stats
            self._cleanup_expired()
            
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = (self._stats["hits"] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "hit_rate": round(hit_rate, 2),
                "sets": self._stats["sets"],
                "deletes": self._stats["deletes"],
                "evictions": self._stats["evictions"],
                "default_ttl": self.default_ttl
            }
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """
        Get memory usage information.
        
        Returns:
            Dictionary of memory usage statistics
        """
        import sys
        
        with self._lock:
            total_size = 0
            for item in self._cache.values():
                total_size += sys.getsizeof(item["value"])
            
            return {
                "items": len(self._cache),
                "estimated_memory_bytes": total_size,
                "average_item_size": total_size // len(self._cache) if self._cache else 0
            }
