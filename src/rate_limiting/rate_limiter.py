"""
Rate limiting implementation for the Kindle Sync application.

Provides rate limiting capabilities to prevent abuse and ensure fair usage.
"""

import time
import asyncio
from typing import Dict, Any, Optional, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass
from loguru import logger

from ..caching import get_cache


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    remaining: int
    reset_time: float
    retry_after: Optional[float] = None


class RateLimiter(ABC):
    """Abstract base class for rate limiters."""
    
    @abstractmethod
    async def is_allowed(self, key: str, limit: int, window: int) -> RateLimitResult:
        """
        Check if a request is allowed under the rate limit.
        
        Args:
            key: Unique identifier for the rate limit
            limit: Maximum number of requests allowed
            window: Time window in seconds
            
        Returns:
            RateLimitResult indicating if request is allowed
        """
        pass


class SlidingWindowRateLimiter(RateLimiter):
    """Rate limiter using sliding window algorithm."""
    
    def __init__(self, cache_backend=None):
        """
        Initialize sliding window rate limiter.
        
        Args:
            cache_backend: Cache backend to use for storage
        """
        self.cache = cache_backend or get_cache()
        self.key_prefix = "rate_limit:"
    
    def _make_key(self, key: str) -> str:
        """Create a prefixed cache key."""
        return f"{self.key_prefix}{key}"
    
    async def is_allowed(self, key: str, limit: int, window: int) -> RateLimitResult:
        """
        Check if a request is allowed using sliding window algorithm.
        
        Args:
            key: Unique identifier for the rate limit
            limit: Maximum number of requests allowed
            window: Time window in seconds
            
        Returns:
            RateLimitResult indicating if request is allowed
        """
        cache_key = self._make_key(key)
        current_time = time.time()
        window_start = current_time - window
        
        try:
            # Get existing timestamps
            timestamps = await self.cache.get(cache_key) or []
            
            # Filter out old timestamps
            timestamps = [ts for ts in timestamps if ts > window_start]
            
            # Check if under limit
            if len(timestamps) < limit:
                # Add current timestamp
                timestamps.append(current_time)
                
                # Store updated timestamps
                await self.cache.set(cache_key, timestamps, window)
                
                return RateLimitResult(
                    allowed=True,
                    remaining=limit - len(timestamps),
                    reset_time=current_time + window
                )
            else:
                # Rate limit exceeded
                oldest_timestamp = min(timestamps)
                retry_after = oldest_timestamp + window - current_time
                
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_time=oldest_timestamp + window,
                    retry_after=max(0, retry_after)
                )
                
        except Exception as e:
            logger.error(f"Rate limiter error for key {key}: {e}")
            # Fail open - allow request if rate limiter fails
            return RateLimitResult(
                allowed=True,
                remaining=limit - 1,
                reset_time=current_time + window
            )


class TokenBucketRateLimiter(RateLimiter):
    """Rate limiter using token bucket algorithm."""
    
    def __init__(self, cache_backend=None):
        """
        Initialize token bucket rate limiter.
        
        Args:
            cache_backend: Cache backend to use for storage
        """
        self.cache = cache_backend or get_cache()
        self.key_prefix = "token_bucket:"
    
    def _make_key(self, key: str) -> str:
        """Create a prefixed cache key."""
        return f"{self.key_prefix}{key}"
    
    async def is_allowed(self, key: str, limit: int, window: int) -> RateLimitResult:
        """
        Check if a request is allowed using token bucket algorithm.
        
        Args:
            key: Unique identifier for the rate limit
            limit: Maximum number of requests allowed (bucket capacity)
            window: Time window in seconds (refill rate)
            
        Returns:
            RateLimitResult indicating if request is allowed
        """
        cache_key = self._make_key(key)
        current_time = time.time()
        
        try:
            # Get bucket state
            bucket_data = await self.cache.get(cache_key)
            
            if bucket_data is None:
                # Initialize new bucket
                bucket_data = {
                    "tokens": limit,
                    "last_refill": current_time
                }
            else:
                # Calculate tokens to add based on time elapsed
                time_elapsed = current_time - bucket_data["last_refill"]
                tokens_to_add = (time_elapsed / window) * limit
                
                # Refill bucket (don't exceed capacity)
                bucket_data["tokens"] = min(limit, bucket_data["tokens"] + tokens_to_add)
                bucket_data["last_refill"] = current_time
            
            # Check if tokens available
            if bucket_data["tokens"] >= 1:
                # Consume a token
                bucket_data["tokens"] -= 1
                
                # Store updated bucket state
                await self.cache.set(cache_key, bucket_data, window * 2)
                
                return RateLimitResult(
                    allowed=True,
                    remaining=int(bucket_data["tokens"]),
                    reset_time=current_time + window
                )
            else:
                # No tokens available
                time_until_refill = window * (1 - bucket_data["tokens"])
                
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_time=current_time + time_until_refill,
                    retry_after=time_until_refill
                )
                
        except Exception as e:
            logger.error(f"Token bucket rate limiter error for key {key}: {e}")
            # Fail open - allow request if rate limiter fails
            return RateLimitResult(
                allowed=True,
                remaining=limit - 1,
                reset_time=current_time + window
            )


class FixedWindowRateLimiter(RateLimiter):
    """Rate limiter using fixed window algorithm."""
    
    def __init__(self, cache_backend=None):
        """
        Initialize fixed window rate limiter.
        
        Args:
            cache_backend: Cache backend to use for storage
        """
        self.cache = cache_backend or get_cache()
        self.key_prefix = "fixed_window:"
    
    def _make_key(self, key: str, window_start: int) -> str:
        """Create a prefixed cache key with window."""
        return f"{self.key_prefix}{key}:{window_start}"
    
    async def is_allowed(self, key: str, limit: int, window: int) -> RateLimitResult:
        """
        Check if a request is allowed using fixed window algorithm.
        
        Args:
            key: Unique identifier for the rate limit
            limit: Maximum number of requests allowed
            window: Time window in seconds
            
        Returns:
            RateLimitResult indicating if request is allowed
        """
        current_time = time.time()
        window_start = int(current_time // window) * window
        window_end = window_start + window
        
        cache_key = self._make_key(key, window_start)
        
        try:
            # Get current count for this window
            count = await self.cache.get(cache_key) or 0
            
            if count < limit:
                # Increment count
                count += 1
                await self.cache.set(cache_key, count, window)
                
                return RateLimitResult(
                    allowed=True,
                    remaining=limit - count,
                    reset_time=window_end
                )
            else:
                # Rate limit exceeded
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_time=window_end,
                    retry_after=window_end - current_time
                )
                
        except Exception as e:
            logger.error(f"Fixed window rate limiter error for key {key}: {e}")
            # Fail open - allow request if rate limiter fails
            return RateLimitResult(
                allowed=True,
                remaining=limit - 1,
                reset_time=window_end
            )


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def initialize_rate_limiter(limiter_type: str = "sliding_window", cache_backend=None) -> RateLimiter:
    """
    Initialize global rate limiter.
    
    Args:
        limiter_type: Type of rate limiter ("sliding_window", "token_bucket", "fixed_window")
        cache_backend: Cache backend to use
        
    Returns:
        Initialized rate limiter
    """
    global _rate_limiter
    
    if limiter_type == "sliding_window":
        _rate_limiter = SlidingWindowRateLimiter(cache_backend)
    elif limiter_type == "token_bucket":
        _rate_limiter = TokenBucketRateLimiter(cache_backend)
    elif limiter_type == "fixed_window":
        _rate_limiter = FixedWindowRateLimiter(cache_backend)
    else:
        raise ValueError(f"Unknown rate limiter type: {limiter_type}")
    
    return _rate_limiter


def get_rate_limiter() -> Optional[RateLimiter]:
    """
    Get the global rate limiter instance.
    
    Returns:
        Rate limiter instance or None if not initialized
    """
    global _rate_limiter
    return _rate_limiter


def get_limiter() -> RateLimiter:
    """
    Get the global rate limiter, initializing with default if needed.
    
    Returns:
        Rate limiter instance
    """
    global _rate_limiter
    
    if _rate_limiter is None:
        _rate_limiter = SlidingWindowRateLimiter()
    
    return _rate_limiter
