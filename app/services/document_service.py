"""Document CRUD: upload validation, listing, retrieval and deletion."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.constants import DocumentStatus
from app.exceptions import AppError
from app.logger import get_logger
from app.models.document import Document
from app.services.storage_service import StorageService

logger = get_logger("document_service")

SUPPORTED_CONTENT_TYPES = {"application/pdf"}


class DocumentService:
    """Application logic for the document lifecycle (excluding ingestion)."""

    def __init__(self, db: AsyncSession, storage: StorageService) -> None:
        self._db = db
        self._storage = storage

    async def create_document(self, filename: str, content_type: str, content: bytes) -> Document:
        self._validate(filename, content_type, content)
        document = Document(
            filename=filename,
            content_type=content_type or "application/pdf",
            size_bytes=len(content),
            status=DocumentStatus.QUEUED.value,
        )
        self._db.add(document)
        # Commit explicitly (not just flush): the caller schedules a background
        # ingestion task right after this returns, and FastAPI runs
        # BackgroundTasks *before* the request's get_db() dependency commits —
        # so without an explicit commit here, the background task's own
        # session cannot see this row yet.
        await self._db.commit()
        logger.info("document created: %s (%s)", document.id, filename)
        return document

    async def list_documents(self, limit: int, offset: int) -> tuple[list[Document], int]:
        stmt = select(Document).order_by(Document.created_at.desc()).limit(limit).offset(offset)
        items = list((await self._db.scalars(stmt)).all())
        total = int(await self._db.scalar(select(func.count()).select_from(Document)) or 0)
        return items, total

    async def get_document(self, document_id: uuid.UUID) -> Document:
        stmt = (
            select(Document)
            .where(Document.id == document_id)
            .options(selectinload(Document.images))
        )
        document = await self._db.scalar(stmt)
        if document is None:
            raise AppError(f"Document {document_id} not found.", status_code=404)
        return document

    async def delete_document(self, document_id: uuid.UUID) -> None:
        document = await self._db.get(Document, document_id)
        if document is None:
            raise AppError(f"Document {document_id} not found.", status_code=404)

        await self._storage.delete_folder(f"doc-{document.id}")
        await self._db.delete(document)
        await self._db.flush()
        logger.info("document deleted: %s", document_id)

    def _validate(self, filename: str, content_type: str, content: bytes) -> None:
        if not content:
            raise AppError("Uploaded file is empty.", status_code=415)

        normalized_type = (content_type or "").split(";")[0].strip().lower()
        if normalized_type not in SUPPORTED_CONTENT_TYPES and not filename.lower().endswith(".pdf"):
            raise AppError(
                f"Unsupported content type '{content_type}'. Only PDF is accepted.", status_code=415
            )

        if len(content) > settings.max_upload_size_bytes:
            raise AppError(
                f"File is {len(content)} bytes; limit is {settings.max_upload_size_bytes} bytes.",
                status_code=413,
            )
