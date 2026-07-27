"""Catalog — MCP servers, tools, skills, and workspace resources."""
from __future__ import annotations

import asyncio
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

    mcp_servers = [
        {"name": "graphify", "status": "connected" if graphify_ok else "offline", "description": "Code graph", "custom": False},
        {"name": "opsora-proxy", "status": "connected" if proxy_ok else "offline", "description": "Model router", "custom": False},
        {"name": "system-monitor", "status": "connected", "description": "Health metrics", "custom": False},
        {"name": "memory-store", "status": "connected", "description": "Agent memory", "custom": False},
    ]

    if user_id is not None:
        from app.services.user_config import list_mcp_servers
        for s in list_mcp_servers(user_id):
            if s.get("enabled", True):
                mcp_servers.append({
                    "id": s.get("id"),
                    "name": s.get("name"),
                    "status": "configured",
                    "description": s.get("description") or s.get("url", ""),
                    "transport": s.get("transport", "http"),
                    "custom": True,
                })

    from app.agent.tools import TOOLS

    tools = [
        {"name": t["name"], "description": t["description"], "category": "agent", "requires_approval": t["name"] in ("run_command", "run_local_command", "provision_instance")}
        for t in TOOLS
    ]

    return {
        "mcp_servers": mcp_servers,
        "tools": tools,
        "skills": [
            {"name": "infra-audit", "description": "Health check all instances", "tools_used": ["system_health", "list_instances"]},
            {"name": "deploy", "description": "Pull, build, deploy, verify", "tools_used": ["run_command", "get_logs"]},
            {"name": "security-scan", "description": "Ports, updates, vulns", "tools_used": ["run_command", "system_health"]},
            {"name": "log-analysis", "description": "Parse recent logs", "tools_used": ["get_logs"]},
        ],
        "resources": {
            "docker_containers": docker_n,
            "mcp_count": len(mcp_servers),
        },
    }


@router.get("")
async def catalog() -> dict:
    return await build_catalog()
