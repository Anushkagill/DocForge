"""Application settings managed via pydantic-settings."""

from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for DocForge.
    
    Reads from environment variables and an optional .env file.
    Follows twelve-factor app principles and fails closed.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Core environment
    ENVIRONMENT: Literal["development", "staging", "production", "test"] = "development"
    LOG_LEVEL: str = "INFO"
    APP_NAME: str = "DocForge"

    # Database (Neon PostgreSQL)
    DATABASE_URL: str = "postgresql://localhost:5432/docforge"

    # Security & Authentication (Argon2id + JWT cookies)
    SECRET_KEY: str = "insecure-dev-secret-key-replace-in-production-before-deploy"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Queue & Broker (Render Key Value / Valkey)
    REDIS_URL: str = "redis://localhost:6379/0"

    # AI Provider (Gemini API)
    GEMINI_API_KEY: str = ""
    GEMINI_EMBEDDING_MODEL: str = "text-embedding-004"
    GEMINI_GENERATION_MODEL: str = "gemini-2.0-flash"

    # Object Storage (Neon Object Storage or Cloudflare R2)
    OBJECT_STORAGE_PROVIDER: Literal["neon", "r2", "local"] = "local"
    OBJECT_STORAGE_ENDPOINT: str = ""
    OBJECT_STORAGE_BUCKET: str = "docforge-documents"
    OBJECT_STORAGE_ACCESS_KEY: str = ""
    OBJECT_STORAGE_SECRET_KEY: str = ""
    OBJECT_STORAGE_REGION: str = "auto"


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton instance of Settings."""
    return Settings()

