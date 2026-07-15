"""PDF -> Markdown parsing (PyMuPDF4LLM) and analysis injection.

Parsing extracts clean markdown plus every embedded image (skipping tiny
decorative ones). ``inject_analysis`` later swaps an image's markdown placeholder
for its rendered vision analysis, tagged with an invisible sentinel comment so the
chunker can link chunks back to images.
"""

from __future__ import annotations

import asyncio
import re
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf
import pymupdf4llm

from app.config import settings
from app.constants import IMAGE_MARKDOWN_PATTERN, IMAGE_SENTINEL_TEMPLATE
from app.exceptions import AppError
from app.logger import get_logger
from app.schemas.vision import ImageAnalysis

logger = get_logger("pdf_service")

_IMAGE_RE = re.compile(IMAGE_MARKDOWN_PATTERN)


@dataclass(slots=True)
class ExtractedImage:
    page_number: int
    image_index: int
    source_ref: str  # exact markdown reference, e.g. "![](/tmp/x-0-0.png)"
    data: bytes
    width: int | None = None
    height: int | None = None
    mime_type: str = "image/png"


@dataclass(slots=True)
class ParsedPage:
    page_number: int
    markdown: str
    images: list[ExtractedImage] = field(default_factory=list)


@dataclass(slots=True)
class ParsedDocument:
    pages: list[ParsedPage]
    page_count: int

    @property
    def images(self) -> list[ExtractedImage]:
        return [img for page in self.pages for img in page.images]


class PdfService:
    """Parse PDFs into page-chunked markdown with extracted images, and inject
    image analysis back into that markdown."""

    async def parse(self, pdf_bytes: bytes) -> ParsedDocument:
        try:
            return await asyncio.to_thread(self._parse_sync, pdf_bytes)
        except Exception as exc:  # noqa: BLE001
            logger.error("pdf parse failed: %s", exc)
            raise AppError(f"Failed to parse PDF: {exc}", status_code=422) from exc

    def _parse_sync(self, pdf_bytes: bytes) -> ParsedDocument:
        with tempfile.TemporaryDirectory(prefix="docvision_") as tmp:
            image_dir = Path(tmp)
            doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
            try:
                page_count = doc.page_count
                page_data = pymupdf4llm.to_markdown(
                    doc,
                    page_chunks=True,
                    write_images=True,
                    image_path=str(image_dir),
                    image_format="png",
                    dpi=150,
                    show_progress=False,
                )
            finally:
                doc.close()

            pages: list[ParsedPage] = []
            global_index = 0
            for i, page in enumerate(page_data):
                markdown = page.get("text", "") if isinstance(page, dict) else str(page)
                page_number = i + 1
                images, global_index = self._collect_images(markdown, page_number, global_index)
                pages.append(ParsedPage(page_number=page_number, markdown=markdown, images=images))

            logger.info("parsed %d pages, %d images", page_count, sum(len(p.images) for p in pages))
            return ParsedDocument(pages=pages, page_count=page_count)

    def _collect_images(
        self, markdown: str, page_number: int, global_index: int
    ) -> tuple[list[ExtractedImage], int]:
        images: list[ExtractedImage] = []
        for match in _IMAGE_RE.finditer(markdown):
            path = Path(match.group("path").strip())
            if not path.exists():
                continue

            width, height = self._dimensions(path)
            if not self._is_meaningful(width, height):
                continue

            try:
                data = path.read_bytes()
            except OSError:
                continue

            images.append(
                ExtractedImage(
                    page_number=page_number,
                    image_index=global_index,
                    source_ref=match.group(0),
                    data=data,
                    width=width,
                    height=height,
                )
            )
            global_index += 1
        return images, global_index

    @staticmethod
    def _dimensions(path: Path) -> tuple[int | None, int | None]:
        try:
            pix = pymupdf.Pixmap(str(path))
            return pix.width, pix.height
        except Exception:  # noqa: BLE001
            return None, None

    @staticmethod
    def _is_meaningful(width: int | None, height: int | None) -> bool:
        if width is None or height is None:
            return True
        return width >= settings.min_image_width and height >= settings.min_image_height

    def inject_analysis(
        self,
        markdown: str,
        *,
        source_ref: str,
        image_id: uuid.UUID,
        analysis: ImageAnalysis,
        cloudinary_url: str | None = None,
    ) -> str:
        """Replace ``source_ref`` in ``markdown`` with the rendered analysis block."""
        sentinel = IMAGE_SENTINEL_TEMPLATE.format(image_id=image_id)
        link = f"\n[View image]({cloudinary_url})\n" if cloudinary_url else ""
        replacement = f"{sentinel}{analysis.to_markdown()}{link}"

        if source_ref and source_ref in markdown:
            return markdown.replace(source_ref, replacement, 1)
        # Placeholder missing (e.g. markdown mutated): append so it's still indexed.
        return f"{markdown}\n\n{replacement}"
