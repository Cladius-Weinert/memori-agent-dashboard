"""Mobile bootstrap + live chat — zero-config client entry point."""
from __future__ import annotations

import json
import os
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.multi_agent import AGENT_LABELS, AGENT_MODELS, AgentRole, run_multi_agent
from app.api.v1.auth import get_current_user
from app.api.v1.catalog import build_catalog
from app.api.v1.models import list_models
from app.api.v1.settings import McpServerIn, ProviderIn
from app.services.user_config import list_mcp_servers, list_providers, upsert_mcp_server, upsert_provider, delete_mcp_server, delete_provider, PROVIDER_PRESETS, ensure_default_mcp_servers
from app.core.config import settings
from app.core.db import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.models import User

router = APIRouter()

MOBILE_EMAIL = os.getenv("MOBILE_AUTO_EMAIL", "mobile@opsora.id")
MOBILE_PASSWORD = os.getenv("MOBILE_AUTO_PASSWORD", "opsora-mobile-2026")
MOBILE_NAME = os.getenv("MOBILE_AUTO_NAME", "Opsora Mobile")


class ChatIn(BaseModel):
    message: str
    model: str | None = None
    mode: str = "chat"
    history: list[dict[str, str]] = []


class ChatOut(BaseModel):
    reply: str
    model: str
    provider: str


def _llm_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.LLM_API_KEY or os.getenv("NVIDIA_API_KEY", ""),
        base_url=settings.LLM_BASE_URL,
    )


async def _ensure_mobile_user(session: AsyncSession) -> User:
    user = await session.scalar(select(User).where(User.email == MOBILE_EMAIL))
    if user:
        ensure_default_mcp_servers(user.id)
        return user
    user = User(
        email=MOBILE_EMAIL,
        full_name=MOBILE_NAME,
        hashed_password=hash_password(MOBILE_PASSWORD),
        role="admin",
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    ensure_default_mcp_servers(user.id)
    return user


@router.get("/bootstrap")
async def mobile_bootstrap(session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """One-call setup: auth token + models + catalog + endpoints."""
    user = await _ensure_mobile_user(session)
    token = create_access_token(user.id)
    models = await list_models()
    cat = await build_catalog(user.id)
    user_providers = list_providers(user.id)

    nvidia_ok = bool(settings.LLM_API_KEY or os.getenv("NVIDIA_API_KEY"))

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user.id, "email": user.email, "full_name": user.full_name},
        "api_version": "1.5",
        "llm": {
            "default_model": settings.LLM_MODEL,
            "base_url": settings.LLM_BASE_URL,
            "nvidia_connected": nvidia_ok,
        },
        "models": models["models"],
        "default_model": models["default"],
        "user_providers": user_providers,
        "catalog": cat,
        "orchestrator": {
            "host": os.getenv("ORCHESTRATOR_HOST", "54.81.31.132"),
            "port": int(os.getenv("ORCHESTRATOR_PORT", "8787")),
        },
        "features": {
            "chat": True,
            "agent": True,
            "multi_agent": True,
            "agent_loop": True,
            "mcp_custom": True,
            "providers_custom": True,
        },
        "agents": {
            role.value: {"model": model, "label": AGENT_LABELS[role]}
            for role, model in AGENT_MODELS.items()
        },
        "provider_presets": PROVIDER_PRESETS,
    }


class MultiAgentIn(BaseModel):
    goal: str
    mode: str = "chat"
    history: list[dict[str, str]] = []


@router.get("/catalog")
async def mobile_catalog(current_user: User = Depends(get_current_user)) -> dict[str, Any]:
    """Authenticated catalog with user MCP servers and tools."""
    return await build_catalog(current_user.id)


@router.post("/multi-agent/run")
async def mobile_multi_agent(
    data: MultiAgentIn,
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """SSE stream: NVIDIA multi-agent loop (orchestrator → visual → executor)."""

    async def stream():
        async for event in run_multi_agent(data.goal, data.mode, data.history, user_id=current_user.id):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.post("/chat", response_model=ChatOut)
async def mobile_chat(
    data: ChatIn,
    current_user: User = Depends(get_current_user),
) -> ChatOut:
    """Live LLM chat — NVIDIA / configured provider."""
    client = _llm_client()
    model = data.model or settings.LLM_MODEL

    mode_prompt = {
        "chat": "You are Opsora, an expert cloud operations AI. Be concise, actionable, use markdown sparingly.",
        "plan": "You are Opsora planner. Break the task into numbered steps. Be specific about tools and cloud resources.",
        "research": "You are Opsora researcher. Analyze from multiple angles: infra, cost, security, alternatives.",
    }.get(data.mode, "You are Opsora AI assistant.")

    messages: list[dict[str, str]] = [{"role": "system", "content": mode_prompt}]
    for h in data.history[-10:]:
        if h.get("role") in ("user", "assistant") and h.get("content"):
            messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": data.message})

    resp = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.4,
        max_tokens=2048,
    )
    reply = resp.choices[0].message.content or ""
    provider = "NVIDIA" if "nvidia" in settings.LLM_BASE_URL else "custom"
    return ChatOut(reply=reply, model=model, provider=provider)


@router.post("/chat/stream")
async def mobile_chat_stream(
    data: ChatIn,
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """SSE streaming chat for mobile."""
    client = _llm_client()
    model = data.model or settings.LLM_MODEL

    mode_prompt = {
        "chat": "You are Opsora, an expert cloud operations AI. Be concise and actionable.",
        "plan": "You are Opsora planner. Output numbered steps with tool names.",
        "research": "You are Opsora researcher. Multi-angle analysis.",
    }.get(data.mode, "You are Opsora AI.")

    messages: list[dict[str, str]] = [{"role": "system", "content": mode_prompt}]
    for h in data.history[-10:]:
        if h.get("role") in ("user", "assistant") and h.get("content"):
            messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": data.message})

    async def generate():
        stream = await client.chat.completions.create(
            model=model, messages=messages, temperature=0.4, max_tokens=2048, stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                yield f"data: {json.dumps({'type': 'token', 'content': delta})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'model': model})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/settings/providers")
async def mobile_list_providers(current_user: User = Depends(get_current_user)) -> dict[str, Any]:
    return {"providers": list_providers(current_user.id), "presets": PROVIDER_PRESETS}


@router.post("/settings/providers")
async def mobile_save_provider(
    data: ProviderIn,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return {"provider": upsert_provider(current_user.id, data.model_dump())}


@router.delete("/settings/providers/{provider_id}")
async def mobile_delete_provider(
    provider_id: str,
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    delete_provider(current_user.id, provider_id)
    return {"status": "deleted"}


@router.get("/settings/mcp")
async def mobile_list_mcp(current_user: User = Depends(get_current_user)) -> dict[str, Any]:
    servers = list_mcp_servers(current_user.id)
    return {"servers": [s for s in servers if not s.get("builtin") and s.get("transport") != "builtin"]}


@router.post("/settings/mcp")
async def mobile_save_mcp(
    data: McpServerIn,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return {"server": upsert_mcp_server(current_user.id, data.model_dump())}


@router.delete("/settings/mcp/{server_id}")
async def mobile_delete_mcp(
    server_id: str,
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    delete_mcp_server(current_user.id, server_id)
    return {"status": "deleted"}


@router.post("/settings/mcp/{server_id}/test")
async def mobile_test_mcp(
    server_id: str,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Test builtin (terminal/github) or custom MCP server."""
    from app.agent.tools import run_local_command, github_run
    from app.services.user_config import get_mcp_auth, list_mcp_servers

    if server_id in ("builtin-terminal", "terminal"):
        result = await run_local_command("echo opsora-terminal-ok")
        return {"ok": result.get("exit_code") == 0, "server": "terminal", "result": result}

    if server_id in ("builtin-github", "github"):
        token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        if not token:
            return {"ok": False, "server": "github", "error": "GITHUB_TOKEN not set on API host"}
        result = await github_run("auth status")
        ok = result.get("exit_code") == 0 or bool(token)
        return {
            "ok": ok,
            "server": "github",
            "result": result,
        }

    servers = list_mcp_servers(current_user.id)
    srv = next((s for s in servers if s.get("id") == server_id), None)
    if not srv:
        return {"ok": False, "error": "server not found"}

    if srv.get("builtin") or srv.get("transport") == "builtin":
        name = srv.get("name", "")
        if name == "terminal":
            return await mobile_test_mcp("builtin-terminal", current_user)
        if name == "github":
            return await mobile_test_mcp("builtin-github", current_user)

    token = get_mcp_auth(current_user.id, server_id)
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(srv["url"], headers=headers)
            return {"ok": resp.status_code < 500, "status": resp.status_code, "server": srv["name"]}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "server": srv.get("name")}
