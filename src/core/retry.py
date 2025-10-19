"""Retry mechanisms with exponential backoff."""

import time
from functools import wraps
from typing import Any
from collections.abc import Callable

from loguru import logger



def with_retry(
    max_attempts: int = 3,
    wait_multiplier: float = 1.0,
    wait_min: float = 1.0,
    wait_max: float = 10.0,
    retry_exceptions: tuple[type[Exception], ...] = (Exception,),
    backoff_factor: float = 2.0,
    jitter: bool = True,
) -> Callable:
    """
    Decorator for retry logic with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        wait_multiplier: Base wait time multiplier
        wait_min: Minimum wait time in seconds
        wait_max: Maximum wait time in seconds
        retry_exceptions: Tuple of exception types to retry on
        backoff_factor: Exponential backoff factor
        jitter: Add random jitter to prevent thundering herd

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except retry_exceptions as e:
                    last_exception = e

                    if attempt == max_attempts - 1:
                        # Last attempt, re-raise the exception
                        logger.error(
                            f"Function {func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise

                    # Calculate wait time with exponential backoff
                    wait_time = min(
                        wait_min * (backoff_factor**attempt) * wait_multiplier,
                        wait_max,
                    )

                    # Add jitter to prevent thundering herd
                    if jitter:
                        import random

                        wait_time *= 0.5 + random.random() * 0.5

                    logger.warning(
                        f"Function {func.__name__} failed (attempt {attempt + 1}/{max_attempts}): {e}. "
                        f"Retrying in {wait_time:.2f} seconds..."
                    )

                    time.sleep(wait_time)

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


def retry_on_network_error(
    max_attempts: int = 3, wait_min: float = 2.0, wait_max: float = 30.0
) -> Callable:
    """
    Specialized retry decorator for network-related operations.

    Args:
        max_attempts: Maximum number of retry attempts
        wait_min: Minimum wait time in seconds
        wait_max: Maximum wait time in seconds

    Returns:
        Decorated function with network-specific retry logic
    """
    network_exceptions = (
        ConnectionError,
        TimeoutError,
        OSError,
        # SMTP exceptions
        Exception,  # Will be more specific in implementation
    )

    return with_retry(
        max_attempts=max_attempts,
        wait_min=wait_min,
        wait_max=wait_max,
        retry_exceptions=network_exceptions,
        backoff_factor=2.0,
        jitter=True,
    )


def retry_on_file_error(
    max_attempts: int = 3, wait_min: float = 0.5, wait_max: float = 5.0
) -> Callable:
    """
    Specialized retry decorator for file-related operations.

    Args:
        max_attempts: Maximum number of retry attempts
        wait_min: Minimum wait time in seconds
        wait_max: Maximum wait time in seconds

    Returns:
        Decorated function with file-specific retry logic
    """
    file_exceptions = (
        FileNotFoundError,
        PermissionError,
        OSError,
        BlockingIOError,
    )

    return with_retry(
        max_attempts=max_attempts,
        wait_min=wait_min,
        wait_max=wait_max,
        retry_exceptions=file_exceptions,
        backoff_factor=1.5,
        jitter=False,
    )
