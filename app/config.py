"""Application configuration, loaded from environment variables / .env."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "DocVision"
    app_env: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    cors_origins: str = "*"

    # Database
    postgres_user: str = "docvision"
    postgres_password: str = "docvision"
    postgres_db: str = "docvision"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: str | None = None
    db_echo: bool = False

    # Gemini
    gemini_api_key: str = "changeme"
    gemini_vision_model: str = "gemini-2.5-flash"
    gemini_chat_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "gemini-embedding-001"
    embedding_dimensions: int = 1536
    gemini_max_retries: int = 4
    gemini_temperature: float = 0.2

    # Cloudinary
    cloudinary_cloud_name: str = "changeme"
    cloudinary_api_key: str = "changeme"
    cloudinary_api_secret: str = "changeme"
    cloudinary_folder: str = "docvision"

    # Ingestion / chunking
    chunk_max_tokens: int = 800
    chunk_overlap_tokens: int = 120
    chunk_min_tokens: int = 64
    max_upload_size_mb: int = 50
    min_image_width: int = 48
    min_image_height: int = 48

    # Retrieval / chat
    retrieval_top_k: int = 6
    retrieval_min_score: float = 0.20
    max_images_per_answer: int = 6

    @property
    def async_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sync_database_url(self) -> str:
        return self.async_database_url.replace("+asyncpg", "+psycopg")

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def cors_origins_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
