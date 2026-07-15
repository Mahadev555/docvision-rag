"""Tests for markdown analysis injection."""

from __future__ import annotations

import uuid

from app.schemas.vision import ImageAnalysis
from app.services.pdf_service import PdfService


def test_inject_replaces_placeholder_in_place() -> None:
    pdf_service = PdfService()
    image_id = uuid.uuid4()
    markdown = "Before.\n\n![](/tmp/x-0-0.png)\n\nAfter."
    analysis = ImageAnalysis(summary="A diagram.", image_type="flowchart")

    result = pdf_service.inject_analysis(
        markdown,
        source_ref="![](/tmp/x-0-0.png)",
        image_id=image_id,
        analysis=analysis,
        cloudinary_url="https://cdn.example/x.png",
    )

    assert "![](/tmp/x-0-0.png)" not in result
    assert "Image Analysis" in result
    assert str(image_id) in result
    assert "https://cdn.example/x.png" in result
    assert result.startswith("Before.")
    assert result.rstrip().endswith("After.")


def test_inject_appends_when_placeholder_missing() -> None:
    pdf_service = PdfService()
    image_id = uuid.uuid4()
    markdown = "No placeholder here."
    analysis = ImageAnalysis(summary="Orphan image.")

    result = pdf_service.inject_analysis(
        markdown, source_ref="![](/missing.png)", image_id=image_id, analysis=analysis
    )

    assert "Orphan image." in result
    assert str(image_id) in result
