"""Tests for the structured image-analysis schema & markdown rendering."""

from __future__ import annotations

from app.schemas.vision import ImageAnalysis


def test_to_markdown_includes_populated_sections() -> None:
    analysis = ImageAnalysis(
        image_type="architecture_diagram",
        summary="A three-tier web architecture.",
        technical_description="Client talks to API which talks to DB.",
        components=["Client", "API", "Database"],
        relationships=["Client -> API: HTTPS", "API -> Database: SQL"],
        workflow="Request flows client to API to database and back.",
        technical_keywords=["architecture", "three-tier"],
    )
    md = analysis.to_markdown()

    assert "Image Analysis" in md
    assert "Architecture Diagram" in md
    assert "Client, API, Database" in md
    assert "three-tier" in md
    assert md.strip().endswith("---")


def test_to_markdown_omits_empty_sections() -> None:
    analysis = ImageAnalysis(summary="Just a summary.")
    md = analysis.to_markdown()

    assert "Summary" in md
    assert "Workflow" not in md
    assert "Components" not in md


def test_searchable_text_flattens_all_fields() -> None:
    analysis = ImageAnalysis(
        summary="s",
        technical_description="t",
        ocr_text="o",
        components=["c1", "c2"],
        technical_keywords=["k1"],
    )
    text = analysis.searchable_text()

    for token in ("s", "t", "o", "c1", "c2", "k1"):
        assert token in text
