"""Application configuration via pydantic-settings."""
from __future__ import annotations

from typing import List, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://memori:memori@localhost:5432/memori"
    REDIS_URL: str = "redis://localhost:6379/0"
    JWT_SECRET: str = "dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "meta/llama-3.1-70b-instruct"
    LLM_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    WORKSPACE_ROOT: str = ""
    CORS_ORIGINS: Union[str, List[str]] = "http://localhost:3000"
    VAULT_ADDR: str = ""

    def resolved_workspace_root(self) -> str:
        if self.WORKSPACE_ROOT:
            return self.WORKSPACE_ROOT
        # Default: monorepo root (memori-agent-dashboard)
        from pathlib import Path
        return str(Path(__file__).resolve().parents[4])

    @field_validator("CORS_ORIGINS")
    @classmethod
    def _split_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v


settings = Settings()
