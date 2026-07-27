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

from app.api.v1.auth import get_current_user
from app.api.v1.catalog import catalog as catalog_data
from app.api.v1.models import list_models
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
    return user


@router.get("/bootstrap")
async def mobile_bootstrap(session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """One-call setup: auth token + models + catalog + endpoints."""
    user = await _ensure_mobile_user(session)
    token = create_access_token(user.id)
    models = await list_models()
    cat = await catalog_data()

    nvidia_ok = bool(settings.LLM_API_KEY or os.getenv("NVIDIA_API_KEY"))
    dashscope_ok = bool(os.getenv("DASHSCOPE_API_KEY"))

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user.id, "email": user.email, "full_name": user.full_name},
        "api_version": "1.0",
        "llm": {
            "default_model": settings.LLM_MODEL,
            "base_url": settings.LLM_BASE_URL,
            "nvidia_connected": nvidia_ok,
            "dashscope_connected": dashscope_ok,
        },
        "models": models["models"],
        "default_model": models["default"],
        "catalog": cat,
        "orchestrator": {
            "host": os.getenv("ORCHESTRATOR_HOST", "54.81.31.132"),
            "port": int(os.getenv("ORCHESTRATOR_PORT", "8787")),
        },
        "features": {
            "chat": True,
            "agent": True,
            "mcp_tools": True,
            "orchestrator": True,
            "cloud_consoles": True,
        },
    }


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
