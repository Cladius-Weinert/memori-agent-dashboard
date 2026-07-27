"""Per-user todos — created by users or the agent via tools."""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

CONFIG_ROOT = Path(os.getenv("OPSORA_CONFIG_DIR", "/home/ubuntu/.opsora/users"))


def _todos_path(user_id: int) -> Path:
    d = CONFIG_ROOT / str(user_id)
    d.mkdir(parents=True, exist_ok=True)
    return d / "todos.json"


def _read(user_id: int) -> list[dict[str, Any]]:
    path = _todos_path(user_id)
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _write(user_id: int, rows: list[dict[str, Any]]) -> None:
    _todos_path(user_id).write_text(json.dumps(rows, indent=2), encoding="utf-8")


def list_todos(user_id: int, *, status: str | None = None) -> list[dict[str, Any]]:
    rows = _read(user_id)
    if status:
        rows = [r for r in rows if r.get("status") == status]
    return sorted(rows, key=lambda r: (r.get("status") != "pending", -(r.get("updated_at") or 0)))


def create_todo(
    user_id: int,
    title: str,
    *,
    notes: str = "",
    priority: str = "normal",
    created_by: str = "user",
    status: str = "pending",
) -> dict[str, Any]:
    title = (title or "").strip()
    if not title:
        raise ValueError("title wajib diisi")
    priority = priority if priority in ("low", "normal", "high") else "normal"
    status = status if status in ("pending", "in_progress", "done", "cancelled") else "pending"
    now = time.time()
    tid = f"t_{uuid.uuid4().hex[:10]}"
    item = {
        "id": tid,
        "title": title[:240],
        "notes": (notes or "")[:2000],
        "status": status,
        "priority": priority,
        "created_by": created_by if created_by in ("user", "agent") else "user",
        "created_at": now,
        "updated_at": now,
    }
    rows = _read(user_id)
    rows.insert(0, item)
    _write(user_id, rows)
    return item


def create_todos_bulk(
    user_id: int,
    titles: list[str],
    *,
    created_by: str = "agent",
    priority: str = "normal",
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for title in titles:
        t = (title or "").strip()
        if not t:
            continue
        out.append(create_todo(user_id, t, created_by=created_by, priority=priority))
    return out


def update_todo(user_id: int, todo_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
    rows = _read(user_id)
    for i, row in enumerate(rows):
        if row.get("id") != todo_id:
            continue
        if "title" in patch and patch["title"] is not None:
            title = str(patch["title"]).strip()
            if title:
                row["title"] = title[:240]
        if "notes" in patch and patch["notes"] is not None:
            row["notes"] = str(patch["notes"])[:2000]
        if "status" in patch and patch["status"] in ("pending", "in_progress", "done", "cancelled"):
            row["status"] = patch["status"]
        if "priority" in patch and patch["priority"] in ("low", "normal", "high"):
            row["priority"] = patch["priority"]
        row["updated_at"] = time.time()
        rows[i] = row
        _write(user_id, rows)
        return row
    return None


def delete_todo(user_id: int, todo_id: str) -> bool:
    rows = _read(user_id)
    next_rows = [r for r in rows if r.get("id") != todo_id]
    if len(next_rows) == len(rows):
        return False
    _write(user_id, next_rows)
    return True


def clear_done(user_id: int) -> int:
    rows = _read(user_id)
    keep = [r for r in rows if r.get("status") not in ("done", "cancelled")]
    removed = len(rows) - len(keep)
    if removed:
        _write(user_id, keep)
    return removed
