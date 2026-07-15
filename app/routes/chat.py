"""Chat endpoint — RAG answering with optional server-sent-event streaming."""

from __future__ import annotations

from typing import Annotated

import orjson
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.vectorstore_service import VectorStoreService

router = APIRouter(prefix="/chat", tags=["chat"])


def get_chat_service(db: Annotated[AsyncSession, Depends(get_db)]) -> ChatService:
    vector_store = VectorStoreService(db, EmbeddingService())
    return ChatService(db, vector_store, LLMService())


@router.post(
    "",
    response_model=ChatResponse,
    summary="Ask a question across ingested documents",
    responses={
        200: {
            "description": "Full answer, or an SSE stream when `stream=true`.",
            "content": {"text/event-stream": {}},
        }
    },
)
async def chat(request: ChatRequest, service: Annotated[ChatService, Depends(get_chat_service)]):
    """Answer a query with retrieved sources and relevant images.

    When ``stream`` is true the response is an SSE stream: a ``metadata`` event
    (conversation id, sources, images) first, then incremental ``token`` events,
    then a terminal ``done`` event.
    """
    if request.stream:
        return StreamingResponse(
            _sse_events(service, request),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    return await service.answer(request)


async def _sse_events(service: ChatService, request: ChatRequest):
    async for event in service.stream_answer(request):
        payload = orjson.dumps(event).decode("utf-8")
        yield f"event: {event['type']}\ndata: {payload}\n\n"
