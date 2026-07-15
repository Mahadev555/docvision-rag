"""Tests for the markdown-aware chunker."""

from __future__ import annotations

import uuid

from app.constants import IMAGE_SENTINEL_TEMPLATE
from app.services.chunking_service import ChunkingService


def _chunker(**overrides) -> ChunkingService:
    """Build a ChunkingService with test-friendly token budgets."""
    from app.config import settings

    original = (settings.chunk_max_tokens, settings.chunk_overlap_tokens, settings.chunk_min_tokens)
    settings.chunk_max_tokens = overrides.get("max_tokens", 64)
    settings.chunk_overlap_tokens = overrides.get("overlap_tokens", 8)
    settings.chunk_min_tokens = overrides.get("min_tokens", 1)
    chunker = ChunkingService()
    settings.chunk_max_tokens, settings.chunk_overlap_tokens, settings.chunk_min_tokens = original
    return chunker


def test_chunks_preserve_heading_hierarchy() -> None:
    chunker = _chunker(max_tokens=64, overlap_tokens=8)
    markdown = (
        "# Root\n\n"
        "Intro paragraph.\n\n"
        "## Child A\n\n"
        "Content under child A.\n\n"
        "## Child B\n\n"
        "Content under child B.\n"
    )
    chunks = chunker.chunk_document([(1, markdown)])

    assert chunks, "expected at least one chunk"
    paths = {c.heading_path for c in chunks}
    assert any(p == "Root > Child A" for p in paths)
    assert any(p == "Root > Child B" for p in paths)
    assert all(c.page_number == 1 for c in chunks)


def test_chunk_indices_are_sequential() -> None:
    chunker = _chunker(max_tokens=32, overlap_tokens=4)
    markdown = "\n\n".join(f"Paragraph number {i} with several words." for i in range(20))
    chunks = chunker.chunk_document([(1, markdown)])

    indices = [c.chunk_index for c in chunks]
    assert indices == list(range(len(chunks)))


def test_image_sentinels_are_extracted_and_stripped() -> None:
    chunker = _chunker(max_tokens=128, overlap_tokens=0)
    image_id = uuid.uuid4()
    sentinel = IMAGE_SENTINEL_TEMPLATE.format(image_id=image_id)
    markdown = f"# Section\n\nSome text.\n\n{sentinel}\nImage analysis body.\n"

    chunks = chunker.chunk_document([(2, markdown)])

    collected = [i for c in chunks for i in c.image_ids]
    assert image_id in collected
    assert all(str(image_id) not in c.content for c in chunks)


def test_respects_max_tokens_budget() -> None:
    chunker = _chunker(max_tokens=50, overlap_tokens=5)
    markdown = "\n\n".join(f"Sentence {i} padded with filler words here." for i in range(40))
    chunks = chunker.chunk_document([(1, markdown)])

    assert all(c.token_count <= 120 for c in chunks)
