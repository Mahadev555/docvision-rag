"""A single application error type, mapped to an HTTP response in main.py."""

from __future__ import annotations


class AppError(Exception):
    """Raised by services for expected failure conditions.

    Routes don't need to catch this — the global handler in main.py converts it
    into a JSON error response with the given status code.
    """

    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)
