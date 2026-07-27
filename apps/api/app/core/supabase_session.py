"""Async session shim backed by Supabase PostgREST."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Select

from app.services.supabase_rest import (
    SupabaseRestClient,
    instance_to_row,
    model_table,
    row_to_instance,
)


class SupabaseSession:
    def __init__(self) -> None:
        self._client = SupabaseRestClient()
        self._pending_inserts: list[Any] = []
        self._pending_updates: list[Any] = []
        self._loaded: dict[int, Any] = {}

    async def get(self, model: type, pk: int) -> Any | None:
        row = await self._client.select_one(model_table(model), id=pk)
        if not row:
            return None
        inst = row_to_instance(model, row)
        self._loaded[id(inst)] = inst
        return inst

    async def scalar(self, statement: Select) -> Any | None:
        rows = await self._execute_select(statement)
        return rows[0] if rows else None

    async def execute(self, statement: Select) -> "_SupabaseResult":
        rows = await self._execute_select(statement)
        return _SupabaseResult(rows)

    def add(self, instance: Any) -> None:
        if getattr(instance, "id", None):
            self._pending_updates.append(instance)
        else:
            self._pending_inserts.append(instance)

    async def commit(self) -> None:
        for instance in self._pending_inserts:
            row = instance_to_row(instance)
            row.pop("id", None)
            created = await self._client.insert(model_table(type(instance)), row)
            for col in type(instance).__table__.columns:
                if col.name in created:
                    setattr(
                        instance,
                        col.name if col.name != "metadata" else "metadata_",
                        created[col.name],
                    )
            self._loaded[id(instance)] = instance

        seen: set[int] = set()
        for instance in [*self._pending_updates, *self._loaded.values()]:
            oid = id(instance)
            if oid in seen:
                continue
            seen.add(oid)
            row_id = getattr(instance, "id", None)
            if not row_id:
                continue
            row = instance_to_row(instance)
            row.pop("id", None)
            patch = {k: v for k, v in row.items() if v is not None}
            if hasattr(instance, "updated_at"):
                patch["updated_at"] = datetime.now(timezone.utc).isoformat()
            updated = await self._client.update(model_table(type(instance)), int(row_id), patch)
            for col in type(instance).__table__.columns:
                if col.name in updated:
                    setattr(
                        instance,
                        col.name if col.name != "metadata" else "metadata_",
                        updated[col.name],
                    )

        self._pending_inserts.clear()
        self._pending_updates.clear()

    async def refresh(self, instance: Any) -> None:
        if not getattr(instance, "id", None):
            return
        row = await self._client.select_one(model_table(type(instance)), id=instance.id)
        if row:
            for col in type(instance).__table__.columns:
                if col.name in row:
                    setattr(
                        instance,
                        col.name if col.name != "metadata" else "metadata_",
                        row[col.name],
                    )

    async def _execute_select(self, statement: Select) -> list[Any]:
        model = statement.column_descriptions[0]["entity"]
        table = model_table(model)
        filters: dict[str, Any] = {}
        order: str | None = None

        for clause in getattr(statement, "_where_criteria", ()):
            left = getattr(clause, "left", None)
            right = getattr(clause, "right", None)
            key = getattr(left, "key", None) or getattr(left, "name", None)
            if key and right is not None and hasattr(right, "value"):
                filters[key] = right.value

        for clause in getattr(statement, "_order_by_clauses", ()):
            elem = getattr(clause, "element", clause)
            key = getattr(elem, "key", None) or getattr(elem, "name", None)
            if key:
                direction = "desc" if getattr(clause, "modifier", None) else "asc"
                order = f"{key}.{direction}"

        rows = await self._client.select_many(table, filters=filters or None, order=order)
        return [row_to_instance(model, row) for row in rows]

    async def __aenter__(self) -> SupabaseSession:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


class _SupabaseResult:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def scalars(self) -> "_SupabaseScalars":
        return _SupabaseScalars(self._rows)


class _SupabaseScalars:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def all(self) -> list[Any]:
        return self._rows

    def first(self) -> Any | None:
        return self._rows[0] if self._rows else None
