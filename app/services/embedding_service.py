"""Gemini embeddings (``gemini-embedding-001``) for chunks and queries."""

from __future__ import annotations

from google import genai
from google.genai import types

from app.config import settings
from app.exceptions import AppError
from app.logger import get_logger
from app.utils.retry import async_retry

logger = get_logger("embedding_service")

_BATCH_SIZE = 32


class EmbeddingService:
    """Embed text with task-type-aware Gemini embeddings."""

    def __init__(self) -> None:
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_embedding_model
        self.dimensions = settings.embedding_dimensions

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed chunks for storage (RETRIEVAL_DOCUMENT task type)."""
        vectors: list[list[float]] = []
        for start in range(0, len(texts), _BATCH_SIZE):
            batch = texts[start : start + _BATCH_SIZE]
            vectors.extend(await self._embed(batch, "RETRIEVAL_DOCUMENT"))
        return vectors

    async def embed_query(self, text: str) -> list[float]:
        """Embed a user query for retrieval (RETRIEVAL_QUERY task type)."""
        result = await self._embed([text], "RETRIEVAL_QUERY")
        return result[0]

    @async_retry(max_attempts=settings.gemini_max_retries)
    async def _embed(self, texts: list[str], task_type: str) -> list[list[float]]:
        try:
            response = await self._client.aio.models.embed_content(
                model=self._model,
                contents=texts,
                config=types.EmbedContentConfig(
                    task_type=task_type, output_dimensionality=self.dimensions
                ),
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("embedding generation failed: %s", exc)
            raise AppError(f"Embedding generation failed: {exc}", status_code=502) from exc

        embeddings = [list(e.values) for e in (response.embeddings or [])]
        if len(embeddings) != len(texts):
            raise AppError("Embedding count mismatch from provider.", status_code=502)
        return embeddings
