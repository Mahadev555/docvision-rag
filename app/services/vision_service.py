"""Gemini Vision — structured image understanding.

Sends each extracted image to Gemini 2.5 Flash and asks for strict JSON matching
:class:`ImageAnalysis`, so results are deterministic to parse and store.
"""

from __future__ import annotations

import json

from google import genai
from google.genai import types

from app.config import settings
from app.logger import get_logger
from app.schemas.vision import ImageAnalysis
from app.utils.retry import async_retry

logger = get_logger("vision_service")

SYSTEM_INSTRUCTION = (
    "You are an expert technical document analyst specialising in diagrams, "
    "architecture visuals, flowcharts, screenshots, charts and UI mockups found "
    "inside enterprise PDFs. Produce a rich, structured understanding of an image "
    "so it becomes fully searchable via semantic search. Transcribe all visible "
    "text verbatim. Never invent details not present in the image."
)

USER_PROMPT = (
    "Analyse the attached image and return ONLY a JSON object matching this schema. "
    "No markdown fences, no commentary.\n\n"
    "{\n"
    '  "image_type": "architecture_diagram | flowchart | sequence_diagram | '
    'screenshot | chart | table | uml | icon | logo | photo | other",\n'
    '  "summary": "1-3 sentence high-level summary",\n'
    '  "technical_description": "detailed description of everything shown",\n'
    '  "ocr_text": "all readable text transcribed verbatim",\n'
    '  "objects": ["distinct visual objects/entities"],\n'
    '  "components": ["named systems, services, nodes or modules"],\n'
    '  "relationships": ["how components connect or flow, e.g. A -> B: request"],\n'
    '  "workflow": "step-by-step process if depicted, else empty",\n'
    '  "important_labels": ["salient labels, legends, annotations"],\n'
    '  "technical_keywords": ["search keywords describing this image"]\n'
    "}"
)


class VisionService:
    """Analyse images with Gemini and return a validated :class:`ImageAnalysis`."""

    def __init__(self) -> None:
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_vision_model

    async def analyze_image(
        self, image_bytes: bytes, mime_type: str = "image/png"
    ) -> ImageAnalysis:
        try:
            raw = await self._generate(image_bytes, mime_type)
        except Exception as exc:  # noqa: BLE001 - degrade gracefully, never break ingestion
            logger.warning("vision analysis failed: %s", exc)
            return ImageAnalysis(summary="Image analysis unavailable.")
        return self._parse(raw)

    @async_retry(max_attempts=settings.gemini_max_retries)
    async def _generate(self, image_bytes: bytes, mime_type: str) -> str:
        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=[types.Part.from_bytes(data=image_bytes, mime_type=mime_type), USER_PROMPT],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=settings.gemini_temperature,
                response_mime_type="application/json",
                response_schema=ImageAnalysis,
            ),
        )
        return response.text or "{}"

    @staticmethod
    def _parse(raw: str) -> ImageAnalysis:
        text = raw.strip().strip("`")
        try:
            return ImageAnalysis.model_validate(json.loads(text))
        except (json.JSONDecodeError, ValueError):
            # Keep the raw text as the summary so it's still searchable.
            return ImageAnalysis(summary=raw[:2000], technical_description=raw[:4000])
