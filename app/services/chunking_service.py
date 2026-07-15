"""Markdown-aware, hierarchy-preserving chunker.

Chunks are produced by splitting markdown into blocks (headers/paragraphs),
tracking the live header hierarchy, and packing blocks up to ``max_tokens`` with a
sliding ``overlap_tokens`` tail. Image sentinels found in a chunk are extracted so
the chunk can be linked back to the images whose analysis it contains.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field

from app.config import settings
from app.constants import IMAGE_SENTINEL_PATTERN
from app.utils.tokens import count_tokens

_HEADER_RE = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<title>.+?)\s*#*$")
_SENTINEL_RE = re.compile(IMAGE_SENTINEL_PATTERN)


@dataclass(slots=True)
class Chunk:
    content: str
    token_count: int
    heading_path: str
    page_number: int | None
    image_ids: list[uuid.UUID] = field(default_factory=list)
    chunk_index: int = 0


@dataclass(slots=True)
class _Block:
    text: str
    tokens: int


class ChunkingService:
    """Split enriched markdown into embeddable chunks."""

    def __init__(self) -> None:
        self._max = settings.chunk_max_tokens
        self._overlap = settings.chunk_overlap_tokens
        self._min = settings.chunk_min_tokens

    def chunk_document(self, pages: list[tuple[int, str]]) -> list[Chunk]:
        """Chunk a whole document from ordered ``(page_number, markdown)`` pages."""
        heading_stack: list[tuple[int, str]] = []
        all_chunks: list[Chunk] = []

        for page_number, markdown in pages:
            page_chunks, heading_stack = self._chunk_page(markdown, page_number, heading_stack)
            all_chunks.extend(page_chunks)

        for index, chunk in enumerate(all_chunks):
            chunk.chunk_index = index
        return all_chunks

    def _chunk_page(
        self, markdown: str, page_number: int, heading_stack: list[tuple[int, str]]
    ) -> tuple[list[Chunk], list[tuple[int, str]]]:
        chunks: list[Chunk] = []
        buffer: list[_Block] = []

        def flush() -> None:
            if not buffer:
                return
            text = "\n\n".join(b.text for b in buffer).strip()
            content, image_ids = self._extract_sentinels(text)
            if not content.strip():
                return
            chunks.append(
                Chunk(
                    content=content,
                    token_count=count_tokens(content),
                    heading_path=self._heading_path(heading_stack),
                    page_number=page_number,
                    image_ids=image_ids,
                )
            )

        for block in self._blocks(markdown):
            header = _HEADER_RE.match(block)
            if header:
                flush()
                buffer = []
                level = len(header.group("hashes"))
                title = header.group("title").strip()
                heading_stack = self._push_heading(heading_stack, level, title)
                buffer.append(_Block(text=block, tokens=count_tokens(block)))
                continue

            block_tokens = count_tokens(block)
            if block_tokens > self._max:
                flush()
                buffer = []
                for piece in self._split_oversized(block):
                    chunks.append(self._materialise(piece, heading_stack, page_number))
                continue

            current_tokens = sum(b.tokens for b in buffer)
            if current_tokens + block_tokens > self._max and buffer:
                flush()
                buffer = self._overlap_tail(buffer)
            buffer.append(_Block(text=block, tokens=block_tokens))

        flush()
        return self._merge_small(chunks), heading_stack

    @staticmethod
    def _blocks(markdown: str) -> list[str]:
        """Split markdown into header lines and paragraph blocks."""
        blocks: list[str] = []
        for raw in re.split(r"\n\s*\n", markdown):
            block = raw.strip()
            if not block:
                continue
            pending: list[str] = []
            for line in block.split("\n"):
                if _HEADER_RE.match(line.strip()):
                    if pending:
                        blocks.append("\n".join(pending).strip())
                        pending = []
                    blocks.append(line.strip())
                else:
                    pending.append(line)
            if pending:
                blocks.append("\n".join(pending).strip())
        return [b for b in blocks if b]

    def _materialise(
        self, text: str, heading_stack: list[tuple[int, str]], page_number: int
    ) -> Chunk:
        content, image_ids = self._extract_sentinels(text)
        return Chunk(
            content=content,
            token_count=count_tokens(content),
            heading_path=self._heading_path(heading_stack),
            page_number=page_number,
            image_ids=image_ids,
        )

    def _overlap_tail(self, buffer: list[_Block]) -> list[_Block]:
        if self._overlap <= 0:
            return []
        tail: list[_Block] = []
        total = 0
        for block in reversed(buffer):
            if total + block.tokens > self._overlap and tail:
                break
            tail.insert(0, block)
            total += block.tokens
        return tail

    def _split_oversized(self, block: str) -> list[str]:
        sentences = re.split(r"(?<=[.!?])\s+", block)
        pieces: list[str] = []
        current: list[str] = []
        current_tokens = 0
        for sentence in sentences:
            st = count_tokens(sentence)
            if current_tokens + st > self._max and current:
                pieces.append(" ".join(current).strip())
                current, current_tokens = [], 0
            current.append(sentence)
            current_tokens += st
        if current:
            pieces.append(" ".join(current).strip())
        return [p for p in pieces if p]

    def _merge_small(self, chunks: list[Chunk]) -> list[Chunk]:
        if not chunks:
            return chunks
        merged: list[Chunk] = []
        for chunk in chunks:
            if (
                merged
                and chunk.token_count < self._min
                and merged[-1].token_count + chunk.token_count <= self._max
            ):
                prev = merged[-1]
                prev.content = f"{prev.content}\n\n{chunk.content}".strip()
                prev.token_count = count_tokens(prev.content)
                prev.image_ids = list(dict.fromkeys(prev.image_ids + chunk.image_ids))
            else:
                merged.append(chunk)
        return merged

    @staticmethod
    def _extract_sentinels(text: str) -> tuple[str, list[uuid.UUID]]:
        ids: list[uuid.UUID] = []
        for match in _SENTINEL_RE.finditer(text):
            try:
                ids.append(uuid.UUID(match.group("image_id")))
            except ValueError:  # pragma: no cover - defensive
                continue
        cleaned = _SENTINEL_RE.sub("", text).strip()
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned, list(dict.fromkeys(ids))

    @staticmethod
    def _push_heading(
        stack: list[tuple[int, str]], level: int, title: str
    ) -> list[tuple[int, str]]:
        new_stack = [(lvl, t) for lvl, t in stack if lvl < level]
        new_stack.append((level, title))
        return new_stack

    @staticmethod
    def _heading_path(stack: list[tuple[int, str]]) -> str:
        return " > ".join(title for _, title in stack)
