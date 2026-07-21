"""Workspace — unified view of all Opsora products and services."""
from __future__ import annotations

import asyncio
import os

from fastapi import APIRouter

router = APIRouter()


async def _check_url(url: str, timeout: float = 3) -> bool:
    try:
        proc = await asyncio.create_subprocess_shell(
            f"curl -sf {url}",
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
        )
        return await asyncio.wait_for(proc.wait(), timeout=timeout) == 0
    except Exception:
        return False


def _has_env(*keys: str) -> bool:
    return any(os.environ.get(k) for k in keys)


@router.get("")
async def workspace() -> dict:
    ollama_ok = await _check_url("http://localhost:11434/api/tags")
    nvidia_ok = _has_env("NVIDIA_API_KEY")
    dashscope_ok = _has_env("DASHSCOPE_API_KEY")
    groq_ok = _has_env("GROQ_API_KEY")
    aws_ok = _has_env("AWS_ACCESS_KEY_ID", "AWS_PROFILE")
    graphify_ok = await _check_url("http://localhost:8090/health") or bool(
        os.popen("which graphify 2>/dev/null").read().strip()
    )

    try:
        proc = await asyncio.create_subprocess_shell(
            "docker ps -q | wc -l",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
        )
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
        docker_n = int(out.strip())
    except Exception:
        docker_n = 0

    products = [
        {"name": "Opsora CLI", "description": "Terminal AI assistant with multi-provider routing", "status": "active", "url": None},
        {"name": "Opsora Dashboard", "description": "Web infrastructure management panel", "status": "active", "url": "/dashboard"},
        {"name": "Opsora Agent", "description": "Autonomous AI agent with planning and delegation", "status": "active", "url": "/ai"},
        {"name": "Opsora Agency", "description": "AI automation service for businesses", "status": "active", "url": None},
        {"name": "Opsora Chat", "description": "Open WebUI integration for conversations", "status": "active", "url": None},
        {"name": "Opsora Workflows", "description": "n8n automation workflows", "status": "active", "url": None},
        {"name": "DPRD Platform", "description": "Constituent management system", "status": "active", "url": None},
        {"name": "Super Agent Hub", "description": "No-code AI agent builder", "status": "beta", "url": None},
    ]

    services = [
        {"name": "NVIDIA NIM", "models": 14, "status": "connected" if nvidia_ok else "disconnected"},
        {"name": "Alibaba DashScope", "models": 3, "status": "connected" if dashscope_ok else "disconnected"},
        {"name": "Groq", "models": 7, "status": "connected" if groq_ok else "disconnected"},
        {"name": "Ollama Local", "models": 7, "status": "connected" if ollama_ok else "disconnected"},
        {"name": "AWS", "profiles": 3, "status": "connected" if aws_ok else "disconnected"},
        {"name": "Graphify", "nodes": 8470, "status": "connected" if graphify_ok else "disconnected"},
    ]

    active = sum(1 for p in products if p["status"] == "active")
    total_models = sum(s.get("models", 0) for s in services)

    return {
        "products": products,
        "services": services,
        "stats": {
            "total_products": len(products),
            "active_products": active,
            "total_models": total_models,
            "total_containers": docker_n,
            "total_endpoints": 28,
            "total_skills": 6,
        },
    }
