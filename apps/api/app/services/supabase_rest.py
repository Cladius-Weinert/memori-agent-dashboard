"""Supabase PostgREST client for agent schema (no direct Postgres password required)."""
from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings

TABLE_BY_MODEL: dict[str, str] = {
    "User": "users",
    "Team": "teams",
    "UserTeam": "user_team",
    "Provider": "providers",
    "Instance": "instances",
    "SSHSession": "ssh_sessions",
    "Command": "commands",
    "Deploy": "deploys",
    "AgentJob": "agent_jobs",
    "AgentAction": "agent_actions",
    "AuditLog": "audit_log",
    "Conversation": "conversations",
    "ConversationMessage": "conversation_messages",
    "TokenUsage": "token_usage",
    "Alert": "alerts",
}


def model_table(model: type) -> str:
    return TABLE_BY_MODEL.get(model.__name__, model.__tablename__)


def instance_to_row(instance: Any) -> dict[str, Any]:
    from datetime import datetime

    row: dict[str, Any] = {}
    for col in instance.__table__.columns:
        py_attr = "metadata_" if col.name == "metadata" else col.name
        val = getattr(instance, py_attr, None)
        if val is None and col.name != "id":
            continue
        if isinstance(val, datetime):
            row[col.name] = val.isoformat()
        else:
            row[col.name] = val
    return row


def row_to_instance(model: type, row: dict[str, Any]) -> Any:
    kwargs: dict[str, Any] = {}
    for col in model.__table__.columns:
        if col.name not in row:
            continue
        key = "metadata_" if col.name == "metadata" else col.name
        kwargs[key] = row[col.name]
    return model(**kwargs)


class SupabaseRestClient:
    def __init__(self) -> None:
        base = settings.SUPABASE_URL.rstrip("/")
        self._rest = f"{base}/rest/v1"
        self._schema = settings.DB_SCHEMA or "agent"
        self._key = settings.SUPABASE_ANON_KEY
        self._headers = {
            "apikey": self._key,
            "Authorization": f"Bearer {self._key}",
            "Accept-Profile": self._schema,
            "Content-Profile": self._schema,
        }

    async def select_one(self, table: str, **filters: Any) -> dict[str, Any] | None:
        params = {f"{k}": f"eq.{v}" for k, v in filters.items()}
        params["limit"] = "1"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{self._rest}/{table}", headers=self._headers, params=params)
            resp.raise_for_status()
            rows = resp.json()
            return rows[0] if rows else None

    async def select_many(
        self,
        table: str,
        *,
        filters: dict[str, Any] | None = None,
        order: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, str] = {}
        for k, v in (filters or {}).items():
            params[k] = f"eq.{v}"
        if order:
            params["order"] = order
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{self._rest}/{table}", headers=self._headers, params=params)
            resp.raise_for_status()
            return resp.json()

    async def insert(self, table: str, row: dict[str, Any]) -> dict[str, Any]:
        headers = {**self._headers, "Prefer": "return=representation"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{self._rest}/{table}", headers=headers, json=row)
            resp.raise_for_status()
            rows = resp.json()
            return rows[0] if isinstance(rows, list) else rows

    async def update(self, table: str, row_id: int, patch: dict[str, Any]) -> dict[str, Any]:
        headers = {**self._headers, "Prefer": "return=representation"}
        params = {"id": f"eq.{row_id}"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.patch(
                f"{self._rest}/{table}", headers=headers, params=params, json=patch
            )
            resp.raise_for_status()
            rows = resp.json()
            return rows[0] if isinstance(rows, list) else rows
