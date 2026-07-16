"""A small retry decorator for flaky external calls (Gemini, Cloudinary)."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from tenacity import AsyncRetrying, RetryCallState, stop_after_attempt, wait_exponential

T = TypeVar("T")

_fallback_wait = wait_exponential(multiplier=1, max=30)


def _retry_delay_seconds(exc: BaseException) -> float | None:
    """Extract a server-suggested retry delay (seconds) from a Gemini 429 error.

    Gemini's ``RESOURCE_EXHAUSTED`` responses include a ``RetryInfo`` detail with
    a ``retryDelay`` like ``"22s"``. Blind exponential backoff (1s/2s/4s/8s) just
    burns the retry budget re-hitting the same per-minute quota, so honouring
    this hint lets more calls actually succeed once the quota window resets.
    """
    details = getattr(exc, "details", None)
    if not isinstance(details, dict):
        return None
    error_details = details.get("error", {}).get("details", [])
    for item in error_details:
        if isinstance(item, dict) and str(item.get("@type", "")).endswith("RetryInfo"):
            delay = item.get("retryDelay")
            if isinstance(delay, str) and delay.endswith("s"):
                try:
                    return float(delay[:-1])
                except ValueError:
                    return None
    return None


def _wait_strategy(retry_state: RetryCallState) -> float:
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    if exc is not None:
        delay = _retry_delay_seconds(exc)
        if delay is not None:
            return delay
    return _fallback_wait(retry_state)


def async_retry(max_attempts: int = 4) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retry an async function, honouring a server-suggested retry delay when
    present and falling back to exponential backoff otherwise."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        async def wrapper(*args: object, **kwargs: object) -> T:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(max_attempts),
                wait=_wait_strategy,
                reraise=True,
            ):
                with attempt:
                    return await func(*args, **kwargs)  # type: ignore[misc]
            raise RuntimeError("unreachable")  # pragma: no cover

        return wrapper  # type: ignore[return-value]

    return decorator
