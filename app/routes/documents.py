"""Document endpoints: upload, list, detail, delete."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.document import (
    DocumentDetail,
    DocumentListResponse,
    DocumentSummary,
    DocumentUploadResponse,
)
from app.services.document_service import DocumentService
from app.services.ingestion_service import IngestionService
from app.services.storage_service import StorageService

router = APIRouter(prefix="/documents", tags=["documents"])


def get_document_service(db: Annotated[AsyncSession, Depends(get_db)]) -> DocumentService:
    return DocumentService(db, StorageService())


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a PDF for multimodal ingestion",
)
async def upload_document(
    background: BackgroundTasks,
    service: Annotated[DocumentService, Depends(get_document_service)],
    file: UploadFile = File(..., description="PDF document to ingest."),
) -> DocumentUploadResponse:
    """Accept a PDF, persist a QUEUED record and process it in the background.

    Returns immediately (202 Accepted); poll ``GET /documents/{id}`` for status.
    """
    content = await file.read()
    document = await service.create_document(
        file.filename or "document.pdf", file.content_type or "application/pdf", content
    )
    background.add_task(_process_in_background, document.id, content)
    return DocumentUploadResponse(
        id=document.id, filename=document.filename, status=document.status
    )


async def _process_in_background(document_id: uuid.UUID, content: bytes) -> None:
    await IngestionService().process_document(document_id, content)


@router.get("", response_model=DocumentListResponse, summary="List uploaded documents")
async def list_documents(
    service: Annotated[DocumentService, Depends(get_document_service)],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> DocumentListResponse:
    items, total = await service.list_documents(limit, offset)
    return DocumentListResponse(
        items=[DocumentSummary.model_validate(d) for d in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentDetail,
    summary="Get a document with its extracted images",
)
async def get_document(
    document_id: uuid.UUID, service: Annotated[DocumentService, Depends(get_document_service)]
) -> DocumentDetail:
    document = await service.get_document(document_id)
    return DocumentDetail.model_validate(document)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document and all derived data",
)
async def delete_document(
    document_id: uuid.UUID, service: Annotated[DocumentService, Depends(get_document_service)]
) -> None:
    await service.delete_document(document_id)
