"""Ingestion pipeline — the core of DocVision.

    parse PDF -> upload images to Cloudinary + analyse with Gemini Vision (concurrently)
    -> inject analysis into markdown -> chunk -> embed -> store in PGVector

Runs in a background task with its own DB session (outside the request lifecycle),
and always leaves the document in a terminal status: ``completed`` or ``failed``.
"""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import DocumentStatus, ImageType
from app.database import async_session_maker
from app.logger import get_logger
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.image import Image
from app.schemas.vision import ImageAnalysis
from app.services.chunking_service import ChunkingService
from app.services.embedding_service import EmbeddingService
from app.services.pdf_service import ExtractedImage, ParsedDocument, PdfService
from app.services.storage_service import StorageService
from app.services.vision_service import VisionService

logger = get_logger("ingestion_service")

# Bound concurrent upload+vision calls to respect provider rate limits.
_MAX_CONCURRENCY = 5


class IngestionService:
    """Coordinate background ingestion of documents."""

    def __init__(self) -> None:
        self._pdf = PdfService()
        self._chunker = ChunkingService()
        self._vision = VisionService()
        self._embeddings = EmbeddingService()
        self._storage = StorageService()

    async def process_document(self, document_id: uuid.UUID, pdf_bytes: bytes) -> None:
        """Run the full ingestion pipeline for a freshly uploaded document."""
        async with async_session_maker() as db:
            document = await db.get(Document, document_id)
            if document is None:
                logger.error("document %s missing before processing", document_id)
                return
            document.status = DocumentStatus.PROCESSING.value
            await db.commit()

        try:
            async with async_session_maker() as db:
                document = await db.get(Document, document_id)
                if document is None:  # pragma: no cover - deleted mid-flight
                    return

                parsed = await self._pdf.parse(pdf_bytes)
                document.page_count = parsed.page_count

                analysed = await self._process_images(db, document_id, parsed)
                enriched_pages = self._enrich_pages(parsed, analysed)

                chunks = await self._persist_chunks(db, document_id, enriched_pages)
                await self._link_images_to_chunks(db, chunks)

                document.image_count = len(analysed)
                document.chunk_count = len(chunks)
                document.status = DocumentStatus.COMPLETED.value
                document.error_message = None
                await db.commit()

            logger.info(
                "ingestion done for %s: %d images, %d chunks",
                document_id,
                len(analysed),
                len(chunks),
            )
        except Exception as exc:  # noqa: BLE001 - never let a background task crash silently
            logger.exception("ingestion failed for %s", document_id)
            await self._mark_failed(document_id, str(exc))

    # --- image processing ----------------------------------------------------
    async def _process_images(
        self, db: AsyncSession, document_id: uuid.UUID, parsed: ParsedDocument
    ) -> list[Image]:
        extracted = parsed.images
        if not extracted:
            return []

        rows: list[tuple[Image, ExtractedImage]] = []
        for ext in extracted:
            row = Image(
                document_id=document_id,
                page_number=ext.page_number,
                image_index=ext.image_index,
                source_ref=ext.source_ref,
                width=ext.width,
                height=ext.height,
            )
            db.add(row)
            rows.append((row, ext))
        await db.flush()

        semaphore = asyncio.Semaphore(_MAX_CONCURRENCY)

        async def upload_and_analyse(row: Image, ext: ExtractedImage):
            async with semaphore:
                public_id = f"doc-{document_id}/img-{ext.image_index}"
                return await asyncio.gather(
                    self._storage.upload_image(ext.data, public_id, str(document_id)),
                    self._vision.analyze_image(ext.data, ext.mime_type),
                )

        results = await asyncio.gather(*(upload_and_analyse(row, ext) for row, ext in rows))

        for (row, _), (upload, analysis) in zip(rows, results, strict=True):
            if upload is not None:
                row.cloudinary_public_id = upload.public_id
                row.cloudinary_url = upload.secure_url
            row.analysis = analysis.model_dump()
            row.description = analysis.searchable_text()
            row.image_type = self._normalise_type(analysis.image_type)

        await db.flush()
        return [row for row, _ in rows]

    def _enrich_pages(self, parsed: ParsedDocument, analysed: list[Image]) -> list[tuple[int, str]]:
        by_ref = {img.source_ref: img for img in analysed if img.source_ref}
        enriched: list[tuple[int, str]] = []
        for page in parsed.pages:
            markdown = page.markdown
            for ext in page.images:
                image = by_ref.get(ext.source_ref)
                if image is None or not image.analysis:
                    continue
                analysis = ImageAnalysis.model_validate(image.analysis)
                markdown = self._pdf.inject_analysis(
                    markdown,
                    source_ref=ext.source_ref,
                    image_id=image.id,
                    analysis=analysis,
                    cloudinary_url=image.cloudinary_url,
                )
            enriched.append((page.page_number, markdown))
        return enriched

    async def _persist_chunks(
        self, db: AsyncSession, document_id: uuid.UUID, enriched_pages: list[tuple[int, str]]
    ) -> list[Chunk]:
        produced = self._chunker.chunk_document(enriched_pages)
        if not produced:
            return []

        embeddings = await self._embeddings.embed_documents([c.content for c in produced])

        rows: list[Chunk] = []
        for produced_chunk, vector in zip(produced, embeddings, strict=True):
            rows.append(
                Chunk(
                    document_id=document_id,
                    chunk_index=produced_chunk.chunk_index,
                    content=produced_chunk.content,
                    token_count=produced_chunk.token_count,
                    heading_path=produced_chunk.heading_path or None,
                    page_number=produced_chunk.page_number,
                    image_ids=produced_chunk.image_ids or None,
                    embedding=vector,
                )
            )
        db.add_all(rows)
        await db.flush()
        return rows

    async def _link_images_to_chunks(self, db: AsyncSession, chunks: list[Chunk]) -> None:
        """Set ``image.chunk_id`` to the chunk that contains its analysis."""
        image_to_chunk: dict[uuid.UUID, uuid.UUID] = {}
        for chunk in chunks:
            for image_id in chunk.image_ids or []:
                image_to_chunk.setdefault(image_id, chunk.id)

        if not image_to_chunk:
            return
        stmt = select(Image).where(Image.id.in_(list(image_to_chunk.keys())))
        for image in (await db.scalars(stmt)).all():
            image.chunk_id = image_to_chunk[image.id]
        await db.flush()

    @staticmethod
    def _normalise_type(image_type: str) -> str:
        value = (image_type or "other").strip().lower().replace(" ", "_")
        valid = {t.value for t in ImageType}
        return value if value in valid else ImageType.OTHER.value

    async def _mark_failed(self, document_id: uuid.UUID, message: str) -> None:
        async with async_session_maker() as db:
            document = await db.get(Document, document_id)
            if document is not None:
                document.status = DocumentStatus.FAILED.value
                document.error_message = message[:2000]
                await db.commit()
