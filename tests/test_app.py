"""Smoke tests for application wiring and the OpenAPI contract."""

from __future__ import annotations

from app.main import create_app


def test_app_builds_and_exposes_routes() -> None:
    app = create_app()
    paths = app.openapi()["paths"]

    assert "/api/v1/health" in paths
    assert "/api/v1/documents/upload" in paths
    assert "/api/v1/documents" in paths
    assert "/api/v1/documents/{document_id}" in paths
    assert "/api/v1/chat" in paths


def test_upload_and_chat_methods_present() -> None:
    app = create_app()
    paths = app.openapi()["paths"]

    assert "post" in paths["/api/v1/documents/upload"]
    assert "post" in paths["/api/v1/chat"]
    assert "delete" in paths["/api/v1/documents/{document_id}"]
