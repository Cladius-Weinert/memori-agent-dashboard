"""Catalog — MCP servers, tools, skills, and workspace resources."""
from __future__ import annotations

import asyncio
import os
import shutil
from typing import Any

from fastapi import APIRouter

router = APIRouter()


async def _check(cmd: str) -> bool:
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
        )
        return await asyncio.wait_for(proc.wait(), timeout=5) == 0
    except Exception:
        return False


async def _docker_count() -> int:
    try:
        proc = await asyncio.create_subprocess_shell(
            "docker ps -q | wc -l",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
        )
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
        return int(out.strip())
    except Exception:
        return 0


async def build_catalog(user_id: int | None = None) -> dict[str, Any]:
    graphify_ok = shutil.which("graphify") is not None
    proxy_ok = await _check("curl -sf http://localhost:8090/health")
    docker_n = await _docker_count()
    gh_ok = shutil.which("gh") is not None or bool(os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN"))

    mcp_servers: list[dict[str, Any]] = [
        {
            "id": "builtin-terminal",
            "name": "terminal",
            "status": "connected",
            "description": "Shell di server API",
            "transport": "builtin",
            "builtin": True,
            "custom": False,
        },
        {
            "id": "builtin-github",
            "name": "github",
            "status": "connected" if gh_ok else "needs_token",
            "description": "GitHub CLI & API",
            "transport": "builtin",
            "builtin": True,
            "custom": False,
        },
        {"name": "graphify", "status": "connected" if graphify_ok else "offline", "description": "Code graph", "custom": False, "builtin": False},
        {"name": "opsora-proxy", "status": "connected" if proxy_ok else "offline", "description": "Model router", "custom": False, "builtin": False},
    ]

    if user_id is not None:
        from app.services.user_config import list_mcp_servers
        seen = {s.get("id") or s.get("name") for s in mcp_servers}
        for s in list_mcp_servers(user_id):
            if not s.get("enabled", True):
                continue
            if s.get("builtin") or s.get("transport") == "builtin":
                continue
            sid = s.get("id") or s.get("name")
            if sid in seen:
                continue
            seen.add(sid)
            mcp_servers.append({
                "id": s.get("id"),
                "name": s.get("name"),
                "status": "configured",
                "description": s.get("description") or s.get("url", ""),
                "transport": s.get("transport", "http"),
                "custom": True,
            })

    from app.agent.tools import TOOLS

    from app.services.elastic_observability import status as elastic_status

    tools = [
        {"name": t["name"], "description": t["description"], "category": "agent", "requires_approval": t["name"] in ("run_command", "run_local_command", "provision_instance")}
        for t in TOOLS
    ]

    return {
        "mcp_servers": mcp_servers,
        "tools": tools,
        "skills": [
            {"name": "infra-audit", "description": "Health check semua instance", "tools_used": ["system_health", "run_local_command"]},
            {"name": "deploy", "description": "Pull, build, deploy, verify", "tools_used": ["run_local_command", "github_run"]},
            {"name": "github-ops", "description": "PR, issue, repo via gh", "tools_used": ["github_run", "github_api"]},
            {"name": "terminal", "description": "Jalankan perintah shell", "tools_used": ["run_local_command", "mcp_invoke"]},
            {"name": "todos", "description": "Buat & kelola checklist tugas", "tools_used": ["todo_create", "todo_list", "todo_update", "todo_delete"]},
        ],
        "resources": {
            "docker_containers": docker_n,
            "mcp_count": len(mcp_servers),
            "elastic": elastic_status(),
        },
    }


@router.get("")
async def catalog() -> dict:
    return await build_catalog()
