"""Tests for settings composition and DSN derivation."""

from __future__ import annotations

from app.config import Settings


def test_async_and_sync_dsn_derivation() -> None:
    settings = Settings()
    assert settings.async_database_url.startswith("postgresql+asyncpg://")
    assert settings.sync_database_url.startswith("postgresql+psycopg://")


def test_cors_origins_wildcard_and_list() -> None:
    assert Settings(cors_origins="*").cors_origins_list == ["*"]
    parsed = Settings(cors_origins="http://a.com, http://b.com").cors_origins_list
    assert parsed == ["http://a.com", "http://b.com"]


def test_upload_size_conversion() -> None:
    settings = Settings(max_upload_size_mb=10)
    assert settings.max_upload_size_bytes == 10 * 1024 * 1024
