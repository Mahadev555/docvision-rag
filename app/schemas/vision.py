"""Structured vision-analysis schema — the contract Gemini Vision must fill."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ImageAnalysis(BaseModel):
    """Structured semantic understanding of a single image."""

    image_type: str = Field(default="other")
    summary: str = Field(default="")
    technical_description: str = Field(default="")
    ocr_text: str = Field(default="")
    objects: list[str] = Field(default_factory=list)
    components: list[str] = Field(default_factory=list)
    relationships: list[str] = Field(default_factory=list)
    workflow: str = Field(default="")
    important_labels: list[str] = Field(default_factory=list)
    technical_keywords: list[str] = Field(default_factory=list)

    def to_markdown(self) -> str:
        """Render the analysis as a readable markdown block for injection."""
        lines: list[str] = ["", "---", "", "**Image Analysis**", ""]

        def section(title: str, value: str) -> None:
            if value.strip():
                lines.append(f"**{title}:** {value.strip()}")
                lines.append("")

        def list_section(title: str, values: list[str]) -> None:
            cleaned = [v.strip() for v in values if v.strip()]
            if cleaned:
                lines.append(f"**{title}:** {', '.join(cleaned)}")
                lines.append("")

        section("Type", self.image_type.replace("_", " ").title())
        section("Summary", self.summary)
        section("Technical Description", self.technical_description)
        section("Workflow", self.workflow)
        list_section("Components", self.components)
        list_section("Relationships", self.relationships)
        list_section("Objects", self.objects)
        list_section("Important Labels", self.important_labels)
        list_section("Keywords", self.technical_keywords)
        section("Text In Image (OCR)", self.ocr_text)

        lines += ["---", ""]
        return "\n".join(lines)

    def searchable_text(self) -> str:
        """Flatten the analysis into one string for keyword/embedding search."""
        parts = [
            self.summary,
            self.technical_description,
            self.workflow,
            self.ocr_text,
            " ".join(self.components),
            " ".join(self.relationships),
            " ".join(self.objects),
            " ".join(self.important_labels),
            " ".join(self.technical_keywords),
        ]
        return " ".join(p for p in parts if p).strip()
