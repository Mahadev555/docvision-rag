"""Shared enums used by models, schemas and services."""

from __future__ import annotations

from enum import StrEnum


class DocumentStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ChatRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class ImageType(StrEnum):
    ARCHITECTURE_DIAGRAM = "architecture_diagram"
    FLOWCHART = "flowchart"
    SEQUENCE_DIAGRAM = "sequence_diagram"
    SCREENSHOT = "screenshot"
    CHART = "chart"
    TABLE = "table"
    UML = "uml"
    ICON = "icon"
    LOGO = "logo"
    PHOTO = "photo"
    OTHER = "other"


# HTML-comment sentinel injected next to an image's analysis so the chunker can
# link the chunk it ends up in back to that image.
IMAGE_SENTINEL_TEMPLATE = "<!--docvision:image:{image_id}-->"
IMAGE_SENTINEL_PATTERN = r"<!--docvision:image:(?P<image_id>[0-9a-fA-F-]{36})-->"
IMAGE_MARKDOWN_PATTERN = r"!\[(?P<alt>[^\]]*)\]\((?P<path>[^)]+)\)"
