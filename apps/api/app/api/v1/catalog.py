"""Catalog — MCP servers, tools, skills, and workspace resources."""
from __future__ import annotations

import asyncio
import shutil

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


@router.get("")
async def catalog() -> dict:
    graphify_ok = shutil.which("graphify") is not None
    proxy_ok = await _check("curl -sf http://localhost:8090/health")
    docker_n = await _docker_count()

    return {
        "mcp_servers": [
            {"name": "graphify", "status": "connected" if graphify_ok else "disconnected", "description": "Code knowledge graph", "stats": {"nodes": 8470, "edges": 15203, "communities": 574}},
            {"name": "opsora-proxy", "status": "connected" if proxy_ok else "disconnected", "description": "AI model router", "stats": {"models": 24, "providers": 3}},
            {"name": "system-monitor", "status": "connected", "description": "Server health metrics", "stats": {}},
            {"name": "memory-store", "status": "connected", "description": "Persistent agent memory", "stats": {}},
        ],
        "tools": [
            {"name": "run_command", "description": "Execute shell commands via SSH", "category": "infrastructure", "requires_approval": True},
            {"name": "list_instances", "description": "List all managed servers", "category": "infrastructure", "requires_approval": False},
            {"name": "get_logs", "description": "Tail server logs", "category": "infrastructure", "requires_approval": False},
            {"name": "system_health", "description": "Local server CPU/RAM/disk metrics", "category": "monitoring", "requires_approval": False},
            {"name": "memory_search", "description": "Search agent memory entries", "category": "memory", "requires_approval": False},
            {"name": "memory_add", "description": "Save to persistent agent memory", "category": "memory", "requires_approval": False},
            {"name": "graphify_query", "description": "Semantic code graph search", "category": "code", "requires_approval": False},
            {"name": "provision_instance", "description": "Create new cloud server", "category": "infrastructure", "requires_approval": True},
        ],
        "skills": [
            {"name": "Infrastructure Audit", "description": "Full health check across all instances", "tools_used": ["system_health", "list_instances", "run_command"]},
            {"name": "Deploy Pipeline", "description": "Git pull → build → deploy → verify", "tools_used": ["run_command", "get_logs"]},
            {"name": "Security Scan", "description": "Check vulnerabilities, open ports, updates", "tools_used": ["run_command", "system_health"]},
            {"name": "Performance Analysis", "description": "CPU/RAM/disk trends and bottleneck detection", "tools_used": ["system_health", "run_command"]},
            {"name": "Log Analysis", "description": "Parse and summarize recent log entries", "tools_used": ["get_logs", "run_command"]},
            {"name": "Backup & Recovery", "description": "Create snapshots, verify integrity", "tools_used": ["run_command", "provision_instance"]},
        ],
        "resources": {
            "docker_containers": docker_n,
            "ai_models": 24,
            "projects_indexed": 15,
            "cloud_accounts": {"aws": 3, "gcp": 1, "digitalocean": 1},
            "databases": ["PostgreSQL 16", "Redis 7", "Qdrant"],
            "services": ["Open WebUI", "n8n", "Guacamole RDP", "Caddy Proxy", "Ollama"],
        },
    }
