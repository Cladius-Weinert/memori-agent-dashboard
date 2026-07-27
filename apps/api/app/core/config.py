"""Application configuration via pydantic-settings."""
from __future__ import annotations

from typing import List, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://memori:memori@localhost:5432/memori"
    DB_SCHEMA: str = "agent"
    SUPABASE_PROJECT_REF: str = ""
    SUPABASE_DB_PASSWORD: str = ""
    SUPABASE_POOLER_HOST: str = "aws-0-ap-southeast-1.pooler.supabase.com"
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

    def resolved_database_url(self) -> str:
        if self.SUPABASE_PROJECT_REF and self.SUPABASE_DB_PASSWORD:
            ref = self.SUPABASE_PROJECT_REF
            pwd = self.SUPABASE_DB_PASSWORD
            host = self.SUPABASE_POOLER_HOST
            return (
                f"postgresql+asyncpg://postgres.{ref}:{pwd}@{host}:6543/postgres?ssl=require"
            )
        return self.DATABASE_URL


settings = Settings()
settings.DATABASE_URL = settings.resolved_database_url()
