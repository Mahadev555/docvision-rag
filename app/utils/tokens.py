"""Token-counting helpers used by the chunker and context builder.

Uses ``tiktoken`` (cl100k_base) as a fast, model-agnostic approximation of token
counts. Gemini uses a different tokenizer, but cl100k is a good enough proxy for
chunk-sizing decisions and avoids a network round-trip per chunk.
"""

from __future__ import annotations

import functools

import tiktoken


@functools.lru_cache(maxsize=1)
def _encoder() -> tiktoken.Encoding:
    return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Return the approximate token count of ``text``."""
    if not text:
        return 0
    return len(_encoder().encode(text))


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Truncate ``text`` so it fits within ``max_tokens`` tokens."""
    if max_tokens <= 0:
        return ""
    enc = _encoder()
    tokens = enc.encode(text)
    if len(tokens) <= max_tokens:
        return text
    return enc.decode(tokens[:max_tokens])
