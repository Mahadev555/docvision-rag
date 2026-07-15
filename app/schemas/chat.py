"""Chat API schemas."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class SourceReference(BaseModel):
    document: str
    document_id: uuid.UUID
    page: int | None = None
    score: float
    chunk_id: uuid.UUID | None = None


class ImageResult(BaseModel):
    url: str
    page: int | None = None
    description: str | None = None
    image_type: str | None = None
    document: str | None = None


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=8000)
    conversation_id: uuid.UUID | None = None
    document_ids: list[uuid.UUID] | None = None
    top_k: int | None = Field(default=None, ge=1, le=20)
    stream: bool = False


class ChatResponse(BaseModel):
    answer: str
    conversation_id: uuid.UUID
    sources: list[SourceReference] = Field(default_factory=list)
    images: list[ImageResult] = Field(default_factory=list)
