"""
Rate limiting decorators for the Kindle Sync application.

Provides decorators for automatic rate limiting of functions.
"""

import asyncio
import functools
from typing import Callable, Optional, Union

from loguru import logger

from .rate_limiter import RateLimitResult, get_limiter


def rate_limit(
    limit: int,
    window: int,
    key_func: Optional[Callable] = None,
    error_message: str = "Rate limit exceeded",
) -> Callable:
    """
    Decorator to rate limit function calls.

    Args:
        limit: Maximum number of requests allowed
        window: Time window in seconds
        key_func: Function to generate rate limit key
        error_message: Error message when rate limit exceeded

    Returns:
        Decorated function
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            limiter = get_limiter()
            if not limiter:
                return await func(*args, **kwargs)

            # Generate rate limit key
            if key_func:
                rate_limit_key = key_func(*args, **kwargs)
            else:
                rate_limit_key = f"{func.__module__}.{func.__name__}"

            # Check rate limit
            result = await limiter.is_allowed(rate_limit_key, limit, window)

            if not result.allowed:
                logger.warning(f"Rate limit exceeded for {rate_limit_key}")
                raise RateLimitExceeded(error_message, retry_after=result.retry_after)

            return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            limiter = get_limiter()
            if not limiter:
                return func(*args, **kwargs)

            # Generate rate limit key
            if key_func:
                rate_limit_key = key_func(*args, **kwargs)
            else:
                rate_limit_key = f"{func.__module__}.{func.__name__}"

            # Check rate limit (sync version)
            try:
                loop = asyncio.get_event_loop()
                result = loop.run_until_complete(
                    limiter.is_allowed(rate_limit_key, limit, window)
                )
            except RuntimeError:
                # No event loop, can't use async rate limiter
                return func(*args, **kwargs)

            if not result.allowed:
                logger.warning(f"Rate limit exceeded for {rate_limit_key}")
                raise RateLimitExceeded(error_message, retry_after=result.retry_after)

            return func(*args, **kwargs)

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def rate_limit_async(
    limit: int,
    window: int,
    key_func: Optional[Callable] = None,
    error_message: str = "Rate limit exceeded",
) -> Callable:
    """
    Decorator specifically for async functions to rate limit calls.

    Args:
        limit: Maximum number of requests allowed
        window: Time window in seconds
        key_func: Function to generate rate limit key
        error_message: Error message when rate limit exceeded

    Returns:
        Decorated async function
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            limiter = get_limiter()
            if not limiter:
                return await func(*args, **kwargs)

            # Generate rate limit key
            if key_func:
                rate_limit_key = key_func(*args, **kwargs)
            else:
                rate_limit_key = f"{func.__module__}.{func.__name__}"

            # Check rate limit
            result = await limiter.is_allowed(rate_limit_key, limit, window)

            if not result.allowed:
                logger.warning(f"Rate limit exceeded for {rate_limit_key}")
                raise RateLimitExceeded(error_message, retry_after=result.retry_after)

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def rate_limit_by_user(
    limit: int,
    window: int,
    user_id_arg: Union[int, str] = 0,
    error_message: str = "Rate limit exceeded",
) -> Callable:
    """
    Decorator to rate limit by user ID.

    Args:
        limit: Maximum number of requests allowed per user
        window: Time window in seconds
        user_id_arg: Index or name of user ID argument
        error_message: Error message when rate limit exceeded

    Returns:
        Decorated function
    """

    def key_func(*args, **kwargs):
        if isinstance(user_id_arg, int):
            # Get user ID from positional argument
            if user_id_arg < len(args):
                return f"user:{args[user_id_arg]}"
        else:
            # Get user ID from keyword argument
            if user_id_arg in kwargs:
                return f"user:{kwargs[user_id_arg]}"

        # Fallback to function name
        return f"user:anonymous"

    return rate_limit(limit, window, key_func, error_message)


def rate_limit_by_ip(
    limit: int, window: int, error_message: str = "Rate limit exceeded"
) -> Callable:
    """
    Decorator to rate limit by IP address.

    Args:
        limit: Maximum number of requests allowed per IP
        window: Time window in seconds
        error_message: Error message when rate limit exceeded

    Returns:
        Decorated function
    """

    def key_func(*args, **kwargs):
        # Try to get IP from request object
        for arg in args:
            if hasattr(arg, "client") and hasattr(arg.client, "host"):
                return f"ip:{arg.client.host}"
            elif hasattr(arg, "remote_addr"):
                return f"ip:{arg.remote_addr}"

        # Fallback to function name
        return f"ip:unknown"

    return rate_limit(limit, window, key_func, error_message)


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, message: str, retry_after: Optional[float] = None):
        """
        Initialize rate limit exception.

        Args:
            message: Error message
            retry_after: Seconds to wait before retrying
        """
        super().__init__(message)
        self.retry_after = retry_after
