"""Tests for retry-delay extraction from Gemini-style 429 errors."""

from __future__ import annotations

from app.utils.retry import _retry_delay_seconds


class _FakeApiError(Exception):
    """Mimics google.genai.errors.APIError's shape (a ``details`` dict)."""

    def __init__(self, details: dict) -> None:
        self.details = details
        super().__init__(str(details))


def _gemini_429(retry_delay: str) -> _FakeApiError:
    return _FakeApiError(
        {
            "error": {
                "code": 429,
                "status": "RESOURCE_EXHAUSTED",
                "details": [
                    {"@type": "type.googleapis.com/google.rpc.Help"},
                    {
                        "@type": "type.googleapis.com/google.rpc.RetryInfo",
                        "retryDelay": retry_delay,
                    },
                ],
            }
        }
    )


def test_extracts_retry_delay_seconds() -> None:
    assert _retry_delay_seconds(_gemini_429("22s")) == 22.0


def test_extracts_fractional_retry_delay() -> None:
    assert _retry_delay_seconds(_gemini_429("1.5s")) == 1.5


def test_returns_none_when_no_retry_info() -> None:
    exc = _FakeApiError({"error": {"code": 500, "details": []}})
    assert _retry_delay_seconds(exc) is None


def test_returns_none_for_unrelated_exception() -> None:
    assert _retry_delay_seconds(ValueError("boom")) is None
