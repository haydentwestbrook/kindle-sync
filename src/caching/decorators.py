"""
Caching decorators for the Kindle Sync application.

Provides decorators for automatic caching of function results.
"""

import functools
import hashlib
import inspect
from typing import Any, Callable, Optional, Union

from loguru import logger

from .cache_manager import get_cache


def cached(
    ttl: Optional[int] = None,
    key_prefix: Optional[str] = None,
    cache_none: bool = False,
):
    """
    Decorator to cache function results.

    Args:
        ttl: Time-to-live in seconds
        key_prefix: Prefix for cache keys
        cache_none: Whether to cache None results

    Returns:
        Decorated function
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            cache = get_cache()
            if not cache:
                return await func(*args, **kwargs)

            # Generate cache key
            cache_key = _generate_cache_key(func, args, kwargs, key_prefix)

            # Try to get from cache
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result

            # Execute function
            result = await func(*args, **kwargs)

            # Cache result if not None or if caching None is allowed
            if result is not None or cache_none:
                await cache.set(cache_key, result, ttl)
                logger.debug(f"Cached result for {func.__name__}")

            return result

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            cache = get_cache()
            if not cache:
                return func(*args, **kwargs)

            # Generate cache key
            cache_key = _generate_cache_key(func, args, kwargs, key_prefix)

            # Try to get from cache (sync version)
            import asyncio

            try:
                loop = asyncio.get_event_loop()
                cached_result = loop.run_until_complete(cache.get(cache_key))
            except RuntimeError:
                # No event loop, can't use async cache
                return func(*args, **kwargs)

            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result

            # Execute function
            result = func(*args, **kwargs)

            # Cache result if not None or if caching None is allowed
            if result is not None or cache_none:
                try:
                    loop.run_until_complete(cache.set(cache_key, result, ttl))
                    logger.debug(f"Cached result for {func.__name__}")
                except RuntimeError:
                    pass  # Can't cache, but function executed successfully

            return result

        # Return appropriate wrapper based on function type
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def cache_invalidate(pattern: Optional[str] = None, key_prefix: Optional[str] = None):
    """
    Decorator to invalidate cache entries after function execution.

    Args:
        pattern: Pattern to match for invalidation
        key_prefix: Prefix for cache keys

    Returns:
        Decorated function
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Execute function
            result = await func(*args, **kwargs)

            # Invalidate cache
            cache = get_cache()
            if cache and pattern:
                await cache.invalidate_pattern(pattern)
                logger.debug(f"Invalidated cache pattern: {pattern}")

            return result

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Execute function
            result = func(*args, **kwargs)

            # Invalidate cache
            cache = get_cache()
            if cache and pattern:
                import asyncio

                try:
                    loop = asyncio.get_event_loop()
                    loop.run_until_complete(cache.invalidate_pattern(pattern))
                    logger.debug(f"Invalidated cache pattern: {pattern}")
                except RuntimeError:
                    pass  # Can't invalidate, but function executed successfully

            return result

        # Return appropriate wrapper based on function type
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def _generate_cache_key(
    func: Callable, args: tuple, kwargs: dict, key_prefix: Optional[str] = None
) -> str:
    """
    Generate a cache key for a function call.

    Args:
        func: Function being called
        args: Function arguments
        kwargs: Function keyword arguments
        key_prefix: Optional key prefix

    Returns:
        Generated cache key
    """
    # Create key components
    key_parts = []

    if key_prefix:
        key_parts.append(key_prefix)

    key_parts.append(func.__module__)
    key_parts.append(func.__name__)

    # Add arguments
    if args:
        key_parts.extend(str(arg) for arg in args)

    # Add keyword arguments (sorted for consistency)
    if kwargs:
        sorted_kwargs = sorted(kwargs.items())
        key_parts.extend(f"{k}={v}" for k, v in sorted_kwargs)

    # Create key string
    key_string = ":".join(key_parts)

    # Hash if key is too long
    if len(key_string) > 250:
        key_string = hashlib.md5(key_string.encode()).hexdigest()

    return key_string
