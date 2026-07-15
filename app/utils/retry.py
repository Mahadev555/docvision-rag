"""A small retry decorator for flaky external calls (Gemini, Cloudinary)."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from tenacity import AsyncRetrying, stop_after_attempt, wait_exponential

T = TypeVar("T")


def async_retry(max_attempts: int = 4) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retry an async function with exponential backoff on any exception."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        async def wrapper(*args: object, **kwargs: object) -> T:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(max_attempts),
                wait=wait_exponential(multiplier=1, max=30),
                reraise=True,
            ):
                with attempt:
                    return await func(*args, **kwargs)  # type: ignore[misc]
            raise RuntimeError("unreachable")  # pragma: no cover

        return wrapper  # type: ignore[return-value]

    return decorator
