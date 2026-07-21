"""Agent memory endpoints — CRUD over project memory files."""
from __future__ import annotations

import os
import re
import time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.v1.auth import get_current_user
from app.models.models import User

router = APIRouter()

MEMORY_DIR = Path("/home/ubuntu/.qwen/projects/-home-ubuntu/memory/project")

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_FM_FIELD_RE = re.compile(r"^(\w+):\s*(.+)$", re.MULTILINE)


def _parse_frontmatter(text: str) -> dict:
    """Return {name, description, type, content} from a memory .md file."""
    meta: dict[str, str] = {}
    content = text
    m = _FRONTMATTER_RE.match(text)
    if m:
        raw = m.group(1)
        for fm in _FM_FIELD_RE.finditer(raw):
            meta[fm.group(1).strip()] = fm.group(2).strip()
        content = text[m.end():]
    return {
        "name": meta.get("name", ""),
        "description": meta.get("description", ""),
        "type": meta.get("type", "project"),
        "content": content.strip(),
    }


class MemoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=300)
    type: str = Field("project", pattern="^(user|feedback|project|reference)$")
    content: str = Field(..., min_length=1)


class MemoryOut(BaseModel):
    filename: str
    name: str
    description: str
    type: str
    content: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/memories", response_model=list[MemoryOut])
async def list_memories(
    _user: User = Depends(get_current_user),
) -> list[dict]:
    """List all project memory entries."""
    results: list[dict] = []
    if not MEMORY_DIR.is_dir():
        return results
    for fp in sorted(MEMORY_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            text = fp.read_text(encoding="utf-8")
        except OSError:
            continue
        entry = _parse_frontmatter(text)
        entry["filename"] = fp.name
        results.append(entry)
    return results


@router.post("/memories", response_model=MemoryOut, status_code=status.HTTP_201_CREATED)
async def create_memory(
    body: MemoryCreate,
    _user: User = Depends(get_current_user),
) -> dict:
    """Create a new project memory file."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", body.name.lower()).strip("-") or "memory"
    filename = f"{slug}.md"
    fp = MEMORY_DIR / filename
    if fp.exists():
        # avoid overwrite — append a timestamp
        filename = f"{slug}-{int(time.time())}.md"
        fp = MEMORY_DIR / filename

    text = (
        f"---\n"
        f"name: {body.name}\n"
        f"description: {body.description}\n"
        f"type: {body.type}\n"
        f"---\n\n"
        f"{body.content}\n"
    )
    fp.write_text(text, encoding="utf-8")
    return {
        "filename": filename,
        "name": body.name,
        "description": body.description,
        "type": body.type,
        "content": body.content,
    }


@router.delete("/memories/{filename}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(
    filename: str,
    _user: User = Depends(get_current_user),
) -> None:
    """Delete a project memory file by filename."""
    # Sanitise to prevent path traversal
    safe = os.path.basename(filename)
    if not safe.endswith(".md"):
        raise HTTPException(status_code=400, detail="filename must end with .md")
    fp = MEMORY_DIR / safe
    if not fp.is_file():
        raise HTTPException(status_code=404, detail="memory file not found")
    fp.unlink()
