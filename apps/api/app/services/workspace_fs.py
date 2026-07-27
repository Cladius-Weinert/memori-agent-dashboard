"""Sandboxed workspace file operations for Opsora Agent IDE."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from app.core.config import settings

MAX_READ_BYTES = 1_048_576
MAX_WRITE_BYTES = 524_288
IGNORE_DIRS = {".git", "node_modules", "__pycache__", ".next", "dist", "build", ".venv", "venv"}


def workspace_root() -> Path:
    return Path(settings.resolved_workspace_root()).resolve()


def resolve_path(rel_path: str = "") -> Path:
    root = workspace_root()
    rel = (rel_path or "").strip().lstrip("/")
    target = (root / rel).resolve()
    if not str(target).startswith(str(root)):
        raise ValueError("path escapes workspace root")
    return target


def list_tree(rel_path: str = "", max_depth: int = 4) -> dict[str, Any]:
    base = resolve_path(rel_path)
    if not base.exists():
        raise FileNotFoundError(rel_path or "/")

    def walk(path: Path, depth: int) -> list[dict[str, Any]]:
        if depth > max_depth or not path.is_dir():
            return []
        entries: list[dict[str, Any]] = []
        try:
            children = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except PermissionError:
            return entries
        for child in children:
            if child.name in IGNORE_DIRS:
                continue
            rel = str(child.relative_to(workspace_root()))
            if child.is_dir():
                entries.append({
                    "name": child.name,
                    "path": rel,
                    "type": "dir",
                    "children": walk(child, depth + 1) if depth < max_depth else [],
                })
            else:
                try:
                    size = child.stat().st_size
                except OSError:
                    size = 0
                entries.append({
                    "name": child.name,
                    "path": rel,
                    "type": "file",
                    "size": size,
                })
        return entries

    return {
        "root": str(workspace_root()),
        "path": rel_path or "",
        "entries": walk(base, 0) if base.is_dir() else [],
    }


def read_file(rel_path: str) -> dict[str, Any]:
    path = resolve_path(rel_path)
    if not path.is_file():
        raise FileNotFoundError(rel_path)
    size = path.stat().st_size
    if size > MAX_READ_BYTES:
        raise ValueError(f"file too large ({size} bytes, max {MAX_READ_BYTES})")
    content = path.read_text(encoding="utf-8", errors="replace")
    return {"path": rel_path, "content": content, "size": size}


def write_file(rel_path: str, content: str) -> dict[str, Any]:
    if len(content.encode("utf-8")) > MAX_WRITE_BYTES:
        raise ValueError("content exceeds max write size")
    path = resolve_path(rel_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return {"path": rel_path, "size": len(content), "written": True}


def search_code(query: str, rel_path: str = "", limit: int = 50) -> dict[str, Any]:
    base = resolve_path(rel_path) if rel_path else workspace_root()
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    matches: list[dict[str, Any]] = []

    def scan_file(fp: Path) -> None:
        nonlocal matches
        if len(matches) >= limit:
            return
        try:
            if fp.stat().st_size > MAX_READ_BYTES:
                return
            text = fp.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeError):
            return
        for i, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line):
                matches.append({
                    "path": str(fp.relative_to(workspace_root())),
                    "line": i,
                    "text": line.strip()[:200],
                })
                if len(matches) >= limit:
                    return

    if base.is_file():
        scan_file(base)
    elif base.is_dir():
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            for name in files:
                if len(matches) >= limit:
                    break
                fp = Path(root) / name
                if fp.suffix in {".pyc", ".png", ".jpg", ".gif", ".woff", ".woff2"}:
                    continue
                scan_file(fp)

    return {"query": query, "matches": matches, "count": len(matches)}
