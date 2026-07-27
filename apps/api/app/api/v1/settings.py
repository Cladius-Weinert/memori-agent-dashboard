"""User settings — LLM providers & custom MCP servers."""
from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.v1.auth import get_current_user
from app.models.models import User
from app.services.user_config import (
    PROVIDER_PRESETS,
    delete_mcp_server,
    delete_provider,
    list_mcp_servers,
    list_providers,
    upsert_mcp_server,
    upsert_provider,
)

router = APIRouter()


class ProviderIn(BaseModel):
    id: str | None = None
    name: str = ""
    preset: str = "custom"
    base_url: str = ""
    default_model: str = ""
    api_key: str = ""
    enabled: bool = True


class McpServerIn(BaseModel):
    id: str | None = None
    name: str
    transport: str = "http"
    url: str
    description: str = ""
    auth_token: str = ""
    enabled: bool = True


@router.get("/presets")
async def provider_presets() -> dict[str, Any]:
    return {"presets": PROVIDER_PRESETS}


@router.get("/providers")
async def get_providers(current_user: User = Depends(get_current_user)) -> dict[str, Any]:
    return {"providers": list_providers(current_user.id)}


@router.post("/providers")
async def save_provider(
    data: ProviderIn,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    saved = upsert_provider(current_user.id, data.model_dump())
    return {"provider": saved}


@router.delete("/providers/{provider_id}")
async def remove_provider(
    provider_id: str,
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    if not delete_provider(current_user.id, provider_id):
        raise HTTPException(404, "not found")
    return {"status": "deleted"}


@router.post("/providers/{provider_id}/test")
async def test_provider(
    provider_id: str,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    from app.services.user_config import get_provider_client

    cfg = get_provider_client(current_user.id, provider_id)
    if not cfg:
        raise HTTPException(400, "provider not configured")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{cfg['base_url'].rstrip('/')}/models",
                headers={"Authorization": f"Bearer {cfg['api_key']}"},
            )
            return {"ok": resp.status_code < 400, "status": resp.status_code}
    except httpx.HTTPError as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/mcp")
async def get_mcp_servers(current_user: User = Depends(get_current_user)) -> dict[str, Any]:
    return {"servers": list_mcp_servers(current_user.id)}


@router.post("/mcp")
async def save_mcp_server(
    data: McpServerIn,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    if not data.url.strip():
        raise HTTPException(400, "url required")
    saved = upsert_mcp_server(current_user.id, data.model_dump())
    return {"server": saved}


@router.delete("/mcp/{server_id}")
async def remove_mcp_server(
    server_id: str,
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    if not delete_mcp_server(current_user.id, server_id):
        raise HTTPException(404, "not found")
    return {"status": "deleted"}


@router.post("/mcp/{server_id}/test")
async def test_mcp_server(
    server_id: str,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    from app.services.user_config import get_mcp_auth

    servers = list_mcp_servers(current_user.id)
    srv = next((s for s in servers if s.get("id") == server_id), None)
    if not srv:
        raise HTTPException(404, "not found")
    token = get_mcp_auth(current_user.id, server_id)
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(srv["url"], headers=headers)
            return {"ok": resp.status_code < 500, "status": resp.status_code}
    except httpx.HTTPError as exc:
        return {"ok": False, "error": str(exc)}
