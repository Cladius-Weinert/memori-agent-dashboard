"""LangGraph-compatible agent tools. Real implementations wired to the SSH pool & provider adapters."""
from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from app.core.db import SessionLocal
from app.models.models import Instance
from app.services.ssh_pool import ssh_pool
from app.services import workspace_fs
from app.agent.safety import check_command, is_destructive


async def list_instances(team_id: int | None = None) -> dict[str, Any]:
    """Return all known instances optionally scoped to a team."""
    async with SessionLocal() as session:
        if team_id is not None:
            result = await session.execute(
                Instance.__table__.select().where(Instance.team_id == team_id)
            )
        else:
            result = await session.execute(Instance.__table__.select())
        rows = result.fetchall()
    return {
        "instances": [
            {
                "id": r.id,
                "name": r.name,
                "host": r.host,
                "status": r.status,
                "tags": r.tags,
                "provider_id": r.provider_id,
            }
            for r in rows
        ]
    }


async def run_command(instance_id: int, command: str) -> dict[str, Any]:
    """Execute a shell command on an instance after safety checks."""
    allowed, reason = check_command(command)
    if not allowed:
        return {"error": f"command blocked by safety layer: {reason}", "allowed": False}

    requires_approval = is_destructive(command)
    if requires_approval:
        # In a fully autonomous setup we still mark it for audit/approval gate.
        return {
            "warning": "destructive command — requires approval",
            "requires_approval": True,
            "command": command,
            "instance_id": instance_id,
        }

    result = await ssh_pool.run_command(instance_id, command)
    return {"allowed": True, "instance_id": instance_id, **result}


async def get_logs(instance_id: int, lines: int = 100) -> dict[str, Any]:
    """Tail recent logs from syslog/journal on the instance."""
    cmd = f"journalctl -n {int(lines)} --no-pager 2>/dev/null || tail -n {int(lines)} /var/log/syslog 2>/dev/null"
    result = await ssh_pool.run_command(instance_id, cmd)
    return {"instance_id": instance_id, "logs": result["stdout"], **result}


async def provision_instance(provider: str, spec: dict[str, Any]) -> dict[str, Any]:
    """Spin up a new instance via the given provider adapter."""
    from app.services.providers import get_adapter
    adapter = get_adapter(provider, **(spec.get("adapter_kwargs", {})))
    return adapter.create_instance(spec)


# ---------------------------------------------------------------------------
# New tools: system_health, memory_search, graphify_query
# ---------------------------------------------------------------------------

_MEMORY_DIR = Path("/home/ubuntu/.qwen/projects/-home-ubuntu/memory/project")
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_FM_FIELD_RE = re.compile(r"^(\w+):\s*(.+)$", re.MULTILINE)


async def system_health() -> dict[str, Any]:
    """Return local server health metrics (CPU, memory, disk, services)."""
    from app.api.v1.system import _gather_health
    return await asyncio.to_thread(_gather_health)


async def memory_search(query: str = "") -> dict[str, Any]:
    """Search project memory files. Returns matching entries."""
    results: list[dict[str, str]] = []
    if not _MEMORY_DIR.is_dir():
        return {"memories": results, "query": query}

    query_lower = query.lower()

    def _read_all() -> list[dict[str, str]]:
        entries: list[dict[str, str]] = []
        for fp in sorted(_MEMORY_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                text = fp.read_text(encoding="utf-8")
            except OSError:
                continue
            meta: dict[str, str] = {"name": "", "description": "", "type": "project"}
            content = text
            m = _FRONTMATTER_RE.match(text)
            if m:
                for fm in _FM_FIELD_RE.finditer(m.group(1)):
                    meta[fm.group(1).strip()] = fm.group(2).strip()
                content = text[m.end():]
            if query_lower and query_lower not in (meta.get("name", "") + meta.get("description", "") + content).lower():
                continue
            entries.append({
                "filename": fp.name,
                "name": meta.get("name", ""),
                "description": meta.get("description", ""),
                "type": meta.get("type", "project"),
                "content": content.strip(),
            })
        return entries

    results = await asyncio.to_thread(_read_all)
    return {"memories": results, "query": query}


async def graphify_query(query: str) -> dict[str, Any]:
    """Run a graphify query and return the result."""
    graphify_root = os.environ.get("GRAPHIFY_ROOT", "/home/ubuntu")

    def _run() -> str:
        return subprocess.check_output(
            ["graphify", "query", query],
            cwd=graphify_root,
            stderr=subprocess.STDOUT,
            timeout=30,
        ).decode("utf-8", errors="replace")

    try:
        output = await asyncio.to_thread(_run)
        return {"query": query, "result": output.strip()}
    except subprocess.CalledProcessError as exc:
        return {"query": query, "error": exc.output.decode("utf-8", errors="replace") if exc.output else str(exc)}
    except subprocess.TimeoutExpired:
        return {"query": query, "error": "graphify query timed out after 30s"}
    except FileNotFoundError:
        return {"query": query, "error": "graphify CLI not found on PATH"}


async def read_file(path: str) -> dict[str, Any]:
    """Read a file from the workspace (relative path)."""
    try:
        return await asyncio.to_thread(workspace_fs.read_file, path)
    except FileNotFoundError:
        return {"error": f"file not found: {path}"}
    except ValueError as exc:
        return {"error": str(exc)}


async def write_file(path: str, content: str) -> dict[str, Any]:
    """Write content to a workspace file. Destructive overwrites require approval."""
    requires_approval = True
    try:
        existing = await asyncio.to_thread(workspace_fs.read_file, path)
        if existing.get("content") != content:
            return {
                "warning": "file write requires approval",
                "requires_approval": requires_approval,
                "path": path,
                "preview": content[:500],
            }
    except FileNotFoundError:
        requires_approval = False

    if requires_approval:
        return {
            "warning": "file write requires approval",
            "requires_approval": True,
            "path": path,
            "preview": content[:500],
        }

    try:
        return await asyncio.to_thread(workspace_fs.write_file, path, content)
    except ValueError as exc:
        return {"error": str(exc)}


async def list_files(path: str = "") -> dict[str, Any]:
    """List workspace directory tree."""
    try:
        return await asyncio.to_thread(workspace_fs.list_tree, path, 3)
    except FileNotFoundError:
        return {"error": f"path not found: {path}"}
    except ValueError as exc:
        return {"error": str(exc)}


async def search_code(query: str, path: str = "") -> dict[str, Any]:
    """Search workspace source files for a query string."""
    return await asyncio.to_thread(workspace_fs.search_code, query, path)


# Tool registry exported for the planner
TOOLS = [
    {
        "name": "list_instances",
        "description": "List all infrastructure instances managed by Memori.",
        "parameters": {"team_id": "int | None"},
        "fn": list_instances,
    },
    {
        "name": "run_command",
        "description": "Run a shell command on a remote instance via SSH. Destructive commands require approval.",
        "parameters": {"instance_id": "int", "command": "str"},
        "fn": run_command,
    },
    {
        "name": "get_logs",
        "description": "Tail recent logs from a given instance.",
        "parameters": {"instance_id": "int", "lines": "int = 100"},
        "fn": get_logs,
    },
    {
        "name": "provision_instance",
        "description": "Create a new instance via a cloud provider adapter.",
        "parameters": {"provider": "str", "spec": "dict"},
        "fn": provision_instance,
    },
    {
        "name": "system_health",
        "description": "Get local server health metrics: CPU, memory, disk, Docker, and service status.",
        "parameters": {},
        "fn": system_health,
    },
    {
        "name": "memory_search",
        "description": "Search agent memory files. Pass an empty query to list all memories.",
        "parameters": {"query": "str"},
        "fn": memory_search,
    },
    {
        "name": "graphify_query",
        "description": "Run a natural-language query against the Graphify knowledge graph and return results.",
        "parameters": {"query": "str"},
        "fn": graphify_query,
    },
    {
        "name": "read_file",
        "description": "Read a source file from the workspace by relative path.",
        "parameters": {"path": "str"},
        "fn": read_file,
    },
    {
        "name": "write_file",
        "description": "Write or overwrite a workspace file. Requires approval for existing files.",
        "parameters": {"path": "str", "content": "str"},
        "fn": write_file,
    },
    {
        "name": "list_files",
        "description": "List files and directories in the workspace.",
        "parameters": {},
        "fn": list_files,
    },
    {
        "name": "search_code",
        "description": "Search workspace files for a text pattern.",
        "parameters": {"query": "str"},
        "fn": search_code,
    },
]


def tool_by_name(name: str) -> dict[str, Any]:
    for t in TOOLS:
        if t["name"] == name:
            return t
    raise KeyError(f"unknown tool: {name}")


_DISPATCH = {t["name"]: t["fn"] for t in TOOLS}


async def call_tool(name: str, **kwargs: Any) -> dict[str, Any]:
    fn = _DISPATCH.get(name)
    if fn is None:
        return {"error": f"unknown tool {name}"}
    try:
        return await fn(**kwargs)  # type: ignore[misc]
    except Exception as exc:  # pragma: no cover
        return {"error": str(exc)}


# JSON schema export for LLM tool-calling
def tools_json() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": {
                    "type": "object",
                    "properties": {
                        k: {"type": "string"} for k in t["parameters"]
                    },
                    "required": list(t["parameters"]),
                },
            },
        }
        for t in TOOLS
    ]


# Re-export json for convenience in planner
__all__ = ["TOOLS", "tool_by_name", "call_tool", "tools_json", "json"]
