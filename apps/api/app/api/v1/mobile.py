"""Mobile bootstrap + live chat — zero-config client entry point."""
from __future__ import annotations

import json
import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
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
from app.services.user_config import (
    list_mcp_servers, list_providers, upsert_mcp_server, upsert_provider,
    delete_mcp_server, delete_provider, PROVIDER_PRESETS, ensure_default_mcp_servers,
    get_orchestrator_settings, save_orchestrator_settings,
)
from app.agent.agent_loop import run_single_model_agent
from app.services.elastic_observability import status as elastic_status
from app.core.config import settings
from app.core.db import get_db
from app.core.security import create_access_token, create_mobile_access_token, hash_password, verify_password
from app.models.models import User

router = APIRouter()

MOBILE_EMAIL = os.getenv("MOBILE_AUTO_EMAIL", "mobile@opsora.id")
MOBILE_PASSWORD = os.getenv("MOBILE_AUTO_PASSWORD", "opsora-mobile-2026")
MOBILE_NAME = os.getenv("MOBILE_AUTO_NAME", "Opsora Mobile")
PERMANENT_GATEWAY = os.getenv(
    "OPSORA_PERMANENT_GATEWAY",
    "https://mwbgkkthwwlcndccnbnf.supabase.co/functions/v1/opsora-api",
)


class MobileLoginIn(BaseModel):
    email: str
    password: str


class MobileRegisterIn(BaseModel):
    email: str
    password: str
    full_name: str | None = None


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
        timeout=60,
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


async def _mobile_payload(session: AsyncSession, user: User) -> dict[str, Any]:
    token = create_mobile_access_token(user.id)
    models = await list_models()
    cat = await build_catalog(user.id)
    user_providers = list_providers(user.id)
    nvidia_ok = bool(settings.LLM_API_KEY or os.getenv("NVIDIA_API_KEY"))
    orch = get_orchestrator_settings(user.id)

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in_days": settings.MOBILE_ACCESS_TOKEN_EXPIRE_DAYS,
        "user": {"id": user.id, "email": user.email, "full_name": user.full_name},
        "api_version": "1.7",
        "permanent_api_url": PERMANENT_GATEWAY,
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
            "host": orch.get("host", "54.81.31.132"),
            "port": orch.get("port", 8787),
            "engine": orch.get("engine", "agent"),
            "loop_model": orch.get("loop_model", settings.LLM_MODEL),
            "max_iterations": orch.get("max_iterations", 12),
            "agent_models": orch.get("agent_models", {}),
        },
        "features": {
            "chat": True,
            "agent": True,
            "multi_agent": True,
            "agent_loop": True,
            "mcp_custom": True,
            "providers_custom": True,
            "todos": True,
            "elastic_observability": elastic_status()["configured"],
        },
        "observability": elastic_status(),
        "agents": {
            role.value: {"model": model, "label": AGENT_LABELS[role]}
            for role, model in AGENT_MODELS.items()
        },
        "provider_presets": PROVIDER_PRESETS,
    }


@router.get("/bootstrap")
async def mobile_bootstrap(session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """One-call setup: auth token + models + catalog. No password needed."""
    user = await _ensure_mobile_user(session)
    return await _mobile_payload(session, user)


@router.post("/login")
async def mobile_login(data: MobileLoginIn, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Login with email + password — returns same payload as bootstrap."""
    user = await session.scalar(select(User).where(User.email == data.email))
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email atau password salah")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Akun tidak aktif")
    ensure_default_mcp_servers(user.id)
    return await _mobile_payload(session, user)


@router.post("/register")
async def mobile_register(data: MobileRegisterIn, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Register new mobile user — returns bootstrap payload on success."""
    existing = await session.scalar(select(User).where(User.email == data.email))
    if existing:
        raise HTTPException(status_code=400, detail="Email sudah terdaftar")
    user = User(
        email=data.email,
        full_name=data.full_name or data.email.split("@")[0],
        hashed_password=hash_password(data.password),
        role="user",
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    ensure_default_mcp_servers(user.id)
    return await _mobile_payload(session, user)


@router.post("/refresh")
async def mobile_refresh(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Refresh JWT — call when token near expiry or after 401."""
    ensure_default_mcp_servers(current_user.id)
    return await _mobile_payload(session, current_user)


class MultiAgentIn(BaseModel):
    goal: str
    mode: str = "chat"
    history: list[dict[str, str]] = []
    model: str | None = None


class AgentLoopIn(BaseModel):
    goal: str
    mode: str = "chat"
    history: list[dict[str, str]] = []
    model: str | None = None
    max_iterations: int = 12
    force_loop: bool = False


class OrchestratorSettingsIn(BaseModel):
    host: str | None = None
    port: int | None = None
    engine: str | None = None  # chat | agent | multi
    loop_model: str | None = None
    max_iterations: int | None = None
    agent_models: dict[str, str] | None = None


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
    orch = get_orchestrator_settings(current_user.id)

    async def stream():
        async for event in run_multi_agent(
            data.goal,
            data.mode,
            data.history,
            user_id=current_user.id,
            custom_models=orch.get("agent_models"),
        ):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.post("/agent-loop/run")
async def mobile_agent_loop(
    data: AgentLoopIn,
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """SSE stream: single-model tool loop (Cursor-style agent)."""
    from app.agent.tools import set_tool_user
    set_tool_user(current_user.id)
    orch = get_orchestrator_settings(current_user.id)
    model = data.model or orch.get("loop_model") or settings.LLM_MODEL
    max_iter = data.max_iterations or orch.get("max_iterations", 12)

    async def stream():
        async for event in run_single_model_agent(
            data.goal,
            model=model,
            mode=data.mode,
            history=data.history,
            max_iterations=max_iter,
            force_loop=data.force_loop,
        ):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.get("/settings/orchestrator")
async def mobile_get_orchestrator(current_user: User = Depends(get_current_user)) -> dict[str, Any]:
    return {"settings": get_orchestrator_settings(current_user.id)}


@router.post("/settings/orchestrator")
async def mobile_save_orchestrator(
    data: OrchestratorSettingsIn,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    saved = save_orchestrator_settings(current_user.id, data.model_dump(exclude_none=True))
    return {"settings": saved}


@router.post("/settings/orchestrator/test")
async def mobile_test_orchestrator(current_user: User = Depends(get_current_user)) -> dict[str, Any]:
    """Health check for VPS orchestrator."""
    import httpx
    orch = get_orchestrator_settings(current_user.id)
    url = f"http://{orch['host']}:{orch['port']}/health"
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            res = await client.get(url)
            return {"ok": res.status_code < 400, "status": res.status_code, "url": url, "body": res.text[:200]}
    except Exception as exc:
        return {"ok": False, "url": url, "error": str(exc)}


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
    if server_id.startswith("builtin-") or server_id in ("terminal", "github"):
        raise HTTPException(status_code=400, detail="Builtin MCP tidak bisa dihapus")
    ok = delete_mcp_server(current_user.id, server_id)
    if not ok:
        raise HTTPException(status_code=404, detail="MCP server tidak ditemukan")
    return {"status": "deleted"}


class TodoIn(BaseModel):
    title: str
    notes: str = ""
    priority: str = "normal"
    status: str = "pending"


class TodoPatch(BaseModel):
    title: str | None = None
    notes: str | None = None
    priority: str | None = None
    status: str | None = None


@router.get("/todos")
async def mobile_list_todos(
    status: str | None = None,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    from app.services.todos import list_todos
    items = list_todos(current_user.id, status=status)
    return {"todos": items, "count": len(items)}


@router.post("/todos")
async def mobile_create_todo(
    data: TodoIn,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    from app.services.todos import create_todo
    try:
        item = create_todo(
            current_user.id,
            data.title,
            notes=data.notes,
            priority=data.priority,
            status=data.status,
            created_by="user",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"todo": item}


@router.patch("/todos/{todo_id}")
async def mobile_update_todo(
    todo_id: str,
    data: TodoPatch,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    from app.services.todos import update_todo
    item = update_todo(current_user.id, todo_id, data.model_dump(exclude_none=True))
    if not item:
        raise HTTPException(status_code=404, detail="Todo tidak ditemukan")
    return {"todo": item}


@router.delete("/todos/{todo_id}")
async def mobile_delete_todo(
    todo_id: str,
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    from app.services.todos import delete_todo
    if not delete_todo(current_user.id, todo_id):
        raise HTTPException(status_code=404, detail="Todo tidak ditemukan")
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
