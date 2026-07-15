"""Image model — an extracted figure with its vision analysis and CDN URL."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.chunk import Chunk
    from app.models.document import Document


class Image(Base):
    __tablename__ = "images"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chunks.id", ondelete="SET NULL"), nullable=True, index=True
    )

    page_number: Mapped[int] = mapped_column(Integer, default=0, index=True)
    image_index: Mapped[int] = mapped_column(Integer, default=0)

    # Exact markdown reference emitted by the parser, used to inject the analysis
    # back into the document at the right spot.
    source_ref: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    cloudinary_public_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    cloudinary_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    analysis: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document: Mapped[Document] = relationship(back_populates="images")
    chunk: Mapped[Chunk | None] = relationship(back_populates="images")
