"""PGVector similarity search over stored chunk embeddings."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.logger import get_logger
from app.models.chunk import Chunk
from app.services.embedding_service import EmbeddingService

logger = get_logger("vectorstore_service")


@dataclass(slots=True)
class ScoredChunk:
    chunk: Chunk
    score: float


class VectorStoreService:
    """Embed a query and find the most similar stored chunks."""

    def __init__(self, db: AsyncSession, embedding_service: EmbeddingService) -> None:
        self._db = db
        self._embeddings = embedding_service

    async def search(
        self,
        query: str,
        *,
        top_k: int = 6,
        min_score: float = 0.0,
        document_ids: list[uuid.UUID] | None = None,
    ) -> list[ScoredChunk]:
        """Return the ``top_k`` most similar chunks by cosine similarity.

        ``document_ids`` optionally scopes the search to a subset of documents
        (metadata filtering).
        """
        query_vector = await self._embeddings.embed_query(query)
        distance = Chunk.embedding.cosine_distance(query_vector)
        score = (1 - distance).label("score")

        stmt = select(Chunk, score).where(Chunk.embedding.isnot(None))
        if document_ids:
            stmt = stmt.where(Chunk.document_id.in_(document_ids))
        stmt = stmt.order_by(distance).limit(top_k)

        rows = await self._db.execute(stmt)
        results = [
            ScoredChunk(chunk=chunk, score=float(sim))
            for chunk, sim in rows.all()
            if float(sim) >= min_score
        ]
        logger.info("vector search: %d hits for top_k=%d", len(results), top_k)
        return results
