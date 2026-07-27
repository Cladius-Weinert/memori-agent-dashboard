"""Async SQLAlchemy engine & session factory."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator, Union

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings, use_supabase_rest

_schema = settings.DB_SCHEMA.strip() if settings.DB_SCHEMA else None
_metadata = MetaData(schema=_schema) if _schema else MetaData()


class Base(DeclarativeBase):
    """Declarative base for all models."""

    metadata = _metadata


def use_supabase_rest() -> bool:
    return bool(settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY)


_connect_args: dict = {}
if _schema:
    _connect_args["server_settings"] = {"search_path": _schema}

engine = None
SessionLocal = None

if not use_supabase_rest():
    engine = create_async_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        future=True,
        connect_args=_connect_args,
    )
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@asynccontextmanager
async def open_session():
    """Context manager for the active database backend."""
    if use_supabase_rest():
        from app.core.supabase_session import SupabaseSession

        async with SupabaseSession() as session:
            yield session
    else:
        async with SessionLocal() as session:
            yield session


@asynccontextmanager
async def get_session() -> AsyncIterator[Union[AsyncSession, "SupabaseSession"]]:
    """Helper context manager for service-layer transactions."""
    if use_supabase_rest():
        from app.core.supabase_session import SupabaseSession

        async with SupabaseSession() as session:
            yield session
    else:
        async with SessionLocal() as session:
            yield session


async def get_db() -> AsyncIterator[Union[AsyncSession, "SupabaseSession"]]:
    """FastAPI dependency that yields an async session."""
    if use_supabase_rest():
        from app.core.supabase_session import SupabaseSession

        async with SupabaseSession() as session:
            yield session
    else:
        async with SessionLocal() as session:
            yield session