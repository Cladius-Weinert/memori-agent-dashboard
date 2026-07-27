"""Async SQLAlchemy engine & session factory."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

_schema = settings.DB_SCHEMA.strip() if settings.DB_SCHEMA else None
_metadata = MetaData(schema=_schema) if _schema else MetaData()


class Base(DeclarativeBase):
    """Declarative base for all models."""

    metadata = _metadata


_connect_args: dict = {}
if _schema:
    _connect_args["server_settings"] = {"search_path": _schema}

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    future=True,
    connect_args=_connect_args,
)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """Helper context manager for service-layer transactions."""
    async with SessionLocal() as session:
        yield session


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields an async session."""
    async with SessionLocal() as session:
        yield session