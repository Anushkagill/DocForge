"""Tests verifying Settings and pydantic-settings configuration loading."""

import os
from docforge.config.settings import Settings


def test_default_settings() -> None:
    """Verify default development settings instantiate cleanly."""
    settings = Settings()
    assert settings.APP_NAME == "DocForge"
    assert settings.ENVIRONMENT in {"development", "staging", "production", "test"}
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES > 0


def test_env_override(monkeypatch) -> None:
    """Verify environment variables override defaults properly."""
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("APP_NAME", "DocForgeTestInstance")

    settings = Settings()
    assert settings.LOG_LEVEL == "DEBUG"
    assert settings.APP_NAME == "DocForgeTestInstance"

