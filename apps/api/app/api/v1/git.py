"""Git API for Opsora Agent IDE."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.v1.auth import get_current_user
from app.models.models import User
from app.services import workspace_git

router = APIRouter()


class GitCommitIn(BaseModel):
    message: str = Field(min_length=1, max_length=500)


class GitAddIn(BaseModel):
    paths: list[str] = Field(default_factory=list)


class GitCheckoutIn(BaseModel):
    branch: str


class TextDiffIn(BaseModel):
    path: str
    content: str


@router.get("/status")
async def status(current_user: User = Depends(get_current_user)) -> dict:
    return await workspace_git.git_status()


@router.get("/diff")
async def diff(
    path: str = "",
    staged: bool = False,
    current_user: User = Depends(get_current_user),
) -> dict:
    return await workspace_git.git_diff(path, staged=staged)


@router.get("/branches")
async def branches(current_user: User = Depends(get_current_user)) -> dict:
    return await workspace_git.git_branches()


@router.get("/log")
async def log(
    limit: int = Query(15, ge=1, le=50),
    current_user: User = Depends(get_current_user),
) -> dict:
    return await workspace_git.git_log(limit)


@router.post("/add")
async def add(
    data: GitAddIn,
    current_user: User = Depends(get_current_user),
) -> dict:
    result = await workspace_git.git_add(data.paths)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error") or result.get("stderr"))
    return result


@router.post("/commit")
async def commit(
    data: GitCommitIn,
    current_user: User = Depends(get_current_user),
) -> dict:
    result = await workspace_git.git_commit(data.message)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error") or result.get("stderr"))
    return result


@router.post("/checkout")
async def checkout(
    data: GitCheckoutIn,
    current_user: User = Depends(get_current_user),
) -> dict:
    result = await workspace_git.git_checkout(data.branch)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error") or result.get("stderr"))
    return result


@router.post("/text-diff")
async def text_diff(
    data: TextDiffIn,
    current_user: User = Depends(get_current_user),
) -> dict:
    from app.services.workspace_fs import read_file

    try:
        existing = read_file(data.path)
        old_content = existing["content"]
    except FileNotFoundError:
        old_content = ""

    lines = workspace_git.text_diff(old_content, data.content)
    return {
        "path": data.path,
        "lines": lines,
        "has_changes": old_content != data.content,
    }
