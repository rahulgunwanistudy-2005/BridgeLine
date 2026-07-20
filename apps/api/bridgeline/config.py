"""Application configuration and the sole environment-reading boundary."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    app_env: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8000, ge=1, le=65535)
    database_url: str = "postgresql+asyncpg://bridgeline:bridgeline@localhost:5432/bridgeline"
    google_api_key: SecretStr | None = None
    llm_max_concurrency: int = Field(default=1, ge=1, le=8)
    llm_min_interval_seconds: float = Field(default=4.1, ge=0.0)
    llm_max_attempts: int = Field(default=3, ge=1, le=10)
    llm_retry_base_seconds: float = Field(default=1.0, gt=0.0)
    ingest_max_upload_bytes: int = Field(default=50 * 1024 * 1024, ge=1)
    ingest_pdf_dpi: int = Field(default=200, ge=72, le=600)
    ingest_ocr_page_concurrency: int = Field(default=1, ge=1, le=2)
    ingest_extraction_pages_per_chunk: int = Field(default=8, ge=1)
    ingest_field_confidence_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    ingest_legibility_threshold: float = Field(default=0.70, ge=0.0, le=1.0)
    ingest_non_iep_rejection_confidence: float = Field(default=0.85, ge=0.0, le=1.0)


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide immutable settings instance."""

    return Settings()
