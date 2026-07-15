"""Chat service — the RAG query flow.

    embed query -> vector search -> assemble context -> LLM answer
    -> attach source & image provenance -> persist conversation turn

Supports a full-response mode and a streaming (SSE) mode.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.constants import ChatRole
from app.exceptions import AppError
from app.models.chat import ChatMessage, Conversation
from app.models.document import Document
from app.models.image import Image
from app.schemas.chat import ChatRequest, ChatResponse, ImageResult, SourceReference
from app.services.llm_service import LLMService
from app.services.vectorstore_service import ScoredChunk, VectorStoreService

SYSTEM_INSTRUCTION = (
    "You are DocVision, an assistant that answers questions about enterprise "
    "documents including their diagrams, architecture visuals, flowcharts and "
    "screenshots. You are given retrieved context passages; some contain "
    "structured 'Image Analysis' blocks describing figures.\n\n"
    "Rules:\n"
    "1. Answer ONLY from the provided context. If insufficient, say so plainly.\n"
    "2. Cite sources inline using [Document, page N] notation.\n"
    "3. When a figure or diagram is relevant, describe it and reference it.\n"
    "4. Be precise, technical and concise. Do not invent facts.\n"
)


class ChatService:
    """Retrieval-augmented question answering over ingested documents."""

    def __init__(self, db: AsyncSession, vector_store: VectorStoreService, llm: LLMService) -> None:
        self._db = db
        self._vector_store = vector_store
        self._llm = llm

    async def answer(self, request: ChatRequest) -> ChatResponse:
        conversation_id = await self._resolve_conversation(request)
        await self._add_message(conversation_id, ChatRole.USER, request.query)

        context, sources, images = await self._retrieve(request)
        history = await self._history_messages(conversation_id)
        messages = [
            *history,
            {"role": "user", "content": self._user_prompt(request.query, context)},
        ]

        answer = await self._llm.generate(messages, system_instruction=SYSTEM_INSTRUCTION)

        await self._persist_answer(conversation_id, answer, sources, images)
        return ChatResponse(
            answer=answer, conversation_id=conversation_id, sources=sources, images=images
        )

    async def stream_answer(self, request: ChatRequest) -> AsyncIterator[dict]:
        """Yield SSE-ready events: metadata first, then answer tokens, then done."""
        conversation_id = await self._resolve_conversation(request)
        await self._add_message(conversation_id, ChatRole.USER, request.query)
        context, sources, images = await self._retrieve(request)

        yield {
            "type": "metadata",
            "conversation_id": str(conversation_id),
            "sources": [s.model_dump(mode="json") for s in sources],
            "images": [i.model_dump(mode="json") for i in images],
        }

        history = await self._history_messages(conversation_id)
        messages = [
            *history,
            {"role": "user", "content": self._user_prompt(request.query, context)},
        ]

        chunks: list[str] = []
        async for token in self._llm.stream(messages, system_instruction=SYSTEM_INSTRUCTION):
            chunks.append(token)
            yield {"type": "token", "content": token}

        await self._persist_answer(conversation_id, "".join(chunks), sources, images)
        yield {"type": "done"}

    # --- internals -----------------------------------------------------------
    async def _resolve_conversation(self, request: ChatRequest) -> uuid.UUID:
        if request.conversation_id is not None:
            conversation = await self._db.get(Conversation, request.conversation_id)
            if conversation is None:
                raise AppError(
                    f"Conversation {request.conversation_id} not found.", status_code=404
                )
            return conversation.id
        conversation = Conversation(title=request.query[:120])
        self._db.add(conversation)
        await self._db.flush()
        return conversation.id

    async def _add_message(
        self, conversation_id: uuid.UUID, role: ChatRole, content: str, **extra
    ) -> None:
        self._db.add(
            ChatMessage(conversation_id=conversation_id, role=role.value, content=content, **extra)
        )
        await self._db.flush()

    async def _persist_answer(
        self,
        conversation_id: uuid.UUID,
        answer: str,
        sources: list[SourceReference],
        images: list[ImageResult],
    ) -> None:
        await self._add_message(
            conversation_id,
            ChatRole.ASSISTANT,
            answer,
            sources=[s.model_dump(mode="json") for s in sources],
            images=[i.model_dump(mode="json") for i in images],
        )

    async def _retrieve(
        self, request: ChatRequest
    ) -> tuple[str, list[SourceReference], list[ImageResult]]:
        top_k = request.top_k or settings.retrieval_top_k
        retrieved = await self._vector_store.search(
            request.query,
            top_k=top_k,
            min_score=settings.retrieval_min_score,
            document_ids=request.document_ids,
        )

        doc_names = await self._document_names(retrieved)
        sources = self._build_sources(retrieved, doc_names)
        images = await self._build_images(retrieved, doc_names)

        passages = [self._passage(rc, doc_names) for rc in retrieved]
        context = (
            "\n\n".join(f"[Context {i}]\n{p}" for i, p in enumerate(passages, start=1))
            or "No context was retrieved."
        )
        return context, sources, images

    async def _document_names(self, retrieved: list[ScoredChunk]) -> dict[uuid.UUID, str]:
        doc_ids = list({rc.chunk.document_id for rc in retrieved})
        if not doc_ids:
            return {}
        docs = (await self._db.scalars(select(Document).where(Document.id.in_(doc_ids)))).all()
        return {doc.id: doc.filename for doc in docs}

    @staticmethod
    def _passage(rc: ScoredChunk, doc_names: dict[uuid.UUID, str]) -> str:
        name = doc_names.get(rc.chunk.document_id, "document")
        page = rc.chunk.page_number
        header = f"Source: {name}" + (f", page {page}" if page else "")
        return f"{header}\n{rc.chunk.content}"

    @staticmethod
    def _build_sources(
        retrieved: list[ScoredChunk], doc_names: dict[uuid.UUID, str]
    ) -> list[SourceReference]:
        sources: list[SourceReference] = []
        seen: set[tuple[uuid.UUID, int | None]] = set()
        for rc in retrieved:
            key = (rc.chunk.document_id, rc.chunk.page_number)
            if key in seen:
                continue
            seen.add(key)
            sources.append(
                SourceReference(
                    document=doc_names.get(rc.chunk.document_id, "document"),
                    document_id=rc.chunk.document_id,
                    page=rc.chunk.page_number,
                    score=round(rc.score, 4),
                    chunk_id=rc.chunk.id,
                )
            )
        return sources

    async def _build_images(
        self, retrieved: list[ScoredChunk], doc_names: dict[uuid.UUID, str]
    ) -> list[ImageResult]:
        image_ids: list[uuid.UUID] = []
        for rc in retrieved:
            for image_id in rc.chunk.image_ids or []:
                if image_id not in image_ids:
                    image_ids.append(image_id)
        if not image_ids:
            return []

        images = (await self._db.scalars(select(Image).where(Image.id.in_(image_ids)))).all()
        results: list[ImageResult] = []
        for image in images:
            if not image.cloudinary_url:
                continue
            results.append(
                ImageResult(
                    url=image.cloudinary_url,
                    page=image.page_number,
                    description=(image.description or "")[:500] or None,
                    image_type=image.image_type,
                    document=doc_names.get(image.document_id),
                )
            )
            if len(results) >= settings.max_images_per_answer:
                break
        return results

    async def _history_messages(self, conversation_id: uuid.UUID) -> list[dict[str, str]]:
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(8)
        )
        recent = list(reversed((await self._db.scalars(stmt)).all()))
        # Exclude the just-added user turn; it's appended separately as the prompt.
        history = recent[:-1]
        return [{"role": m.role, "content": m.content} for m in history]

    @staticmethod
    def _user_prompt(query: str, context: str) -> str:
        return (
            "Answer the question using only the context below.\n\n"
            f"=== CONTEXT ===\n{context}\n=== END CONTEXT ===\n\n"
            f"Question: {query}"
        )
