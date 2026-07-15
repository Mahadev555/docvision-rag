"""Shared pytest fixtures.

Environment defaults are set before the app imports settings so tests never
require a real ``.env`` or live external credentials.
"""

from __future__ import annotations

import os

os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("GEMINI_API_KEY", "test-key")
os.environ.setdefault("EMBEDDING_DIMENSIONS", "768")
os.environ.setdefault("CLOUDINARY_CLOUD_NAME", "test-cloud")
os.environ.setdefault("POSTGRES_HOST", "localhost")

import pytest


@pytest.fixture
def sample_markdown() -> str:
    return (
        "# Architecture Overview\n\n"
        "The system has three tiers.\n\n"
        "## Data Layer\n\n"
        "PostgreSQL with PGVector stores embeddings.\n\n"
        "![](/tmp/doc-0-0.png)\n\n"
        "## API Layer\n\n"
        "FastAPI serves the endpoints.\n"
    )
