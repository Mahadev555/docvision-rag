"""Gemini chat/generation (Gemini 2.5 Flash), with streaming support."""

from __future__ import annotations

from collections.abc import AsyncIterator

from google import genai
from google.genai import types

from app.config import settings
from app.exceptions import AppError
from app.logger import get_logger
from app.utils.retry import async_retry

logger = get_logger("llm_service")

# Gemini uses "model" for assistant turns rather than "assistant".
_ROLE_MAP = {"user": "user", "assistant": "model"}


class LLMService:
    """Generate chat completions, full or streamed."""

    def __init__(self) -> None:
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_chat_model

    def _contents(self, messages: list[dict[str, str]]) -> list[types.Content]:
        return [
            types.Content(
                role=_ROLE_MAP.get(m["role"], "user"),
                parts=[types.Part.from_text(text=m["content"])],
            )
            for m in messages
        ]

    def _config(self, system_instruction: str | None) -> types.GenerateContentConfig:
        return types.GenerateContentConfig(
            system_instruction=system_instruction, temperature=settings.gemini_temperature
        )

    @async_retry(max_attempts=settings.gemini_max_retries)
    async def generate(
        self, messages: list[dict[str, str]], system_instruction: str | None = None
    ) -> str:
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=self._contents(messages),
                config=self._config(system_instruction),
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("chat generation failed: %s", exc)
            raise AppError(f"Chat generation failed: {exc}", status_code=502) from exc
        return response.text or ""

    async def stream(
        self, messages: list[dict[str, str]], system_instruction: str | None = None
    ) -> AsyncIterator[str]:
        try:
            stream = await self._client.aio.models.generate_content_stream(
                model=self._model,
                contents=self._contents(messages),
                config=self._config(system_instruction),
            )
            async for chunk in stream:
                if chunk.text:
                    yield chunk.text
        except Exception as exc:  # noqa: BLE001
            logger.error("chat streaming failed: %s", exc)
            raise AppError(f"Chat streaming failed: {exc}", status_code=502) from exc
