"""Retry utilities with exponential backoff."""

import asyncio
import logging
from collections.abc import Callable
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


def retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 10.0,
    exponential_base: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
):
    """Retry decorator with exponential backoff."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            delay = initial_delay
            last_exception: Exception | None = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        break
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}. Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                    delay = min(delay * exponential_base, max_delay)

            if last_exception is not None:
                raise last_exception
            raise RuntimeError(f"{func.__name__} failed without an exception")

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            import time

            delay = initial_delay
            last_exception: Exception | None = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        break
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}. Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                    delay = min(delay * exponential_base, max_delay)

            if last_exception is not None:
                raise last_exception
            raise RuntimeError(f"{func.__name__} failed without an exception")

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator
