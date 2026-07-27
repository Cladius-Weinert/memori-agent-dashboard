"""Workspace file API for Opsora Agent IDE."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.v1.auth import get_current_user
from app.models.models import User
from app.services import workspace_fs

router = APIRouter()


class FileWriteIn(BaseModel):
    path: str
    content: str


@router.get("/tree")
async def file_tree(
    path: str = "",
    current_user: User = Depends(get_current_user),
) -> dict:
    try:
        return workspace_fs.list_tree(path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="path not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/read")
async def file_read(
    path: str = Query(...),
    current_user: User = Depends(get_current_user),
) -> dict:
    try:
        return workspace_fs.read_file(path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="file not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/write")
async def file_write(
    data: FileWriteIn,
    current_user: User = Depends(get_current_user),
) -> dict:
    try:
        return workspace_fs.write_file(data.path, data.content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/search")
async def file_search(
    q: str = Query(..., min_length=1),
    path: str = "",
    current_user: User = Depends(get_current_user),
) -> dict:
    return workspace_fs.search_code(q, path)
