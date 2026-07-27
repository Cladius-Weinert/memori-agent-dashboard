"""LangGraph-compatible agent tools. Real implementations wired to the SSH pool & provider adapters."""
from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
from contextvars import ContextVar
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from app.core.db import SessionLocal
from app.models.models import Instance
from app.services.ssh_pool import ssh_pool
from app.agent.safety import check_command, is_destructive

_user_id_ctx: ContextVar[int | None] = ContextVar("opsora_user_id", default=None)


def set_tool_user(user_id: int | None) -> None:
    _user_id_ctx.set(user_id)

# Paths the agent may read/write locally.
_ALLOWED_WRITE_ROOTS = (
    Path("/agent"),
    Path("/tmp/opsora-agent"),
    Path("/home/ubuntu/.opsora"),
)
_MAX_FETCH_BYTES = 256_000
_MAX_FILE_BYTES = 512_000
_LOCAL_CMD_TIMEOUT = 60


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


def _resolve_safe_path(raw: str) -> Path | None:
    """Return resolved path if it lies under an allowed root."""
    try:
        p = Path(raw).expanduser().resolve()
    except (OSError, ValueError):
        return None
    for root in _ALLOWED_WRITE_ROOTS:
        try:
            root_resolved = root.resolve()
            p.relative_to(root_resolved)
            return p
        except ValueError:
            continue
    return None


async def webfetch(url: str, method: str = "GET") -> dict[str, Any]:
    """Fetch a URL and return status, headers summary, and truncated body."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return {"error": "only http/https URLs allowed", "url": url}

    try:
        async with httpx.AsyncClient(
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": "Opsora-Agent/1.3"},
        ) as client:
            resp = await client.request(method.upper(), url)
            body = resp.text[:_MAX_FETCH_BYTES]
            return {
                "url": str(resp.url),
                "status": resp.status_code,
                "content_type": resp.headers.get("content-type", ""),
                "body": body,
                "truncated": len(resp.text) > _MAX_FETCH_BYTES,
            }
    except httpx.HTTPError as exc:
        return {"error": str(exc), "url": url}


async def read_file(path: str) -> dict[str, Any]:
    """Read a file from an allowed workspace path."""
    safe = _resolve_safe_path(path)
    if safe is None:
        return {"error": f"path not allowed: {path}", "allowed_roots": [str(r) for r in _ALLOWED_WRITE_ROOTS]}
    if not safe.is_file():
        return {"error": "file not found", "path": str(safe)}

    def _read() -> str:
        return safe.read_text(encoding="utf-8", errors="replace")[:_MAX_FILE_BYTES]

    content = await asyncio.to_thread(_read)
    return {"path": str(safe), "content": content, "truncated": safe.stat().st_size > _MAX_FILE_BYTES}


async def write_file(path: str, content: str, append: bool = False) -> dict[str, Any]:
    """Create or overwrite a file in an allowed workspace path."""
    safe = _resolve_safe_path(path)
    if safe is None:
        return {"error": f"path not allowed: {path}", "allowed_roots": [str(r) for r in _ALLOWED_WRITE_ROOTS]}
    if len(content.encode("utf-8")) > _MAX_FILE_BYTES:
        return {"error": f"content exceeds {_MAX_FILE_BYTES} bytes"}

    def _write() -> dict[str, Any]:
        safe.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append else "w"
        with safe.open(mode, encoding="utf-8") as fh:
            fh.write(content)
        return {"path": str(safe), "bytes": safe.stat().st_size, "append": append}

    return await asyncio.to_thread(_write)


async def run_local_command(command: str, cwd: str | None = None) -> dict[str, Any]:
    """Run a shell command on the API host with safety checks."""
    allowed, reason = check_command(command)
    if not allowed:
        return {"error": f"command blocked: {reason}", "allowed": False, "command": command}

    requires_approval = is_destructive(command)
    if requires_approval:
        return {
            "warning": "destructive command — requires approval",
            "requires_approval": True,
            "command": command,
        }

    workdir = _resolve_safe_path(cwd) if cwd else Path("/agent")
    if workdir is None or not workdir.is_dir():
        workdir = Path("/agent")

    def _run() -> dict[str, Any]:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=str(workdir),
            capture_output=True,
            text=True,
            timeout=_LOCAL_CMD_TIMEOUT,
        )
        return {
            "allowed": True,
            "command": command,
            "cwd": str(workdir),
            "exit_code": proc.returncode,
            "stdout": proc.stdout[-8000:],
            "stderr": proc.stderr[-4000:],
        }

    try:
        return await asyncio.to_thread(_run)
    except subprocess.TimeoutExpired:
        return {"error": f"command timed out after {_LOCAL_CMD_TIMEOUT}s", "command": command}


async def github_run(command: str) -> dict[str, Any]:
    """Run a GitHub CLI (gh) command on the API host."""
    if not command.strip().startswith("gh "):
        command = f"gh {command.strip()}"
    allowed, reason = check_command(command)
    if not allowed:
        return {"error": f"command blocked: {reason}", "command": command}
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    env = os.environ.copy()
    if token:
        env["GH_TOKEN"] = token
        env["GITHUB_TOKEN"] = token

    def _run() -> dict[str, Any]:
        proc = subprocess.run(
            command,
            shell=True,
            cwd="/agent",
            capture_output=True,
            text=True,
            timeout=_LOCAL_CMD_TIMEOUT,
            env=env,
        )
        return {
            "command": command,
            "exit_code": proc.returncode,
            "stdout": proc.stdout[-8000:],
            "stderr": proc.stderr[-4000:],
        }

    try:
        return await asyncio.to_thread(_run)
    except subprocess.TimeoutExpired:
        return {"error": f"github command timed out after {_LOCAL_CMD_TIMEOUT}s", "command": command}
    except FileNotFoundError:
        return {"error": "gh CLI not installed", "command": command}


async def github_api(method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Call GitHub REST API (api.github.com). Path like /repos/owner/repo."""
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if not token:
        return {"error": "GITHUB_TOKEN not configured"}
    if not path.startswith("/"):
        path = f"/{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.request(
                method.upper(),
                f"https://api.github.com{path}",
                headers=headers,
                json=body if body else None,
            )
            text = resp.text[:8000]
            return {"status": resp.status_code, "path": path, "body": text}
    except httpx.HTTPError as exc:
        return {"error": str(exc), "path": path}


async def mcp_invoke(server: str, tool: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    """Call builtin or user-configured MCP server."""
    args = arguments or {}
    if server in ("terminal", "builtin-terminal"):
        cmd = args.get("command", tool if tool not in ("run", "exec") else "")
        if not cmd:
            return {"error": "command required", "server": "terminal"}
        return await run_local_command(cmd, args.get("cwd"))

    if server in ("github", "builtin-github"):
        if args.get("action") == "api" or tool == "api":
            return await github_api(
                args.get("method", "GET"),
                args.get("path", ""),
                args.get("body"),
            )
        return await github_run(args.get("command", tool if tool.startswith("gh") else f"gh {tool}"))

    uid = _user_id_ctx.get()
    if uid is None:
        return {"error": "no user context for MCP"}
    from app.services.user_config import get_mcp_auth, list_mcp_servers

    servers = [s for s in list_mcp_servers(uid) if s.get("enabled", True)]
    target = next((s for s in servers if s.get("name") == server or s.get("id") == server), None)
    if not target:
        return {"error": f"mcp server not found: {server}", "available": [s.get("name") for s in servers]}
    if target.get("builtin") or target.get("transport") == "builtin":
        return {"error": "builtin server — use mcp_invoke with server name terminal or github"}

    token = get_mcp_auth(uid, target["id"])
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    payload = {"tool": tool, "arguments": args}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(target["url"], json=payload, headers=headers)
            return {"server": target["name"], "status": resp.status_code, "result": resp.text[:4000]}
    except httpx.HTTPError as exc:
        return {"error": str(exc), "server": target["name"]}


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
        "name": "webfetch",
        "description": "Fetch a public HTTP/HTTPS URL and return status + body (web research, docs, APIs).",
        "parameters": {"url": "str", "method": "str = GET"},
        "fn": webfetch,
    },
    {
        "name": "read_file",
        "description": "Read a text file from the Opsora workspace (/agent, /tmp/opsora-agent).",
        "parameters": {"path": "str"},
        "fn": read_file,
    },
    {
        "name": "write_file",
        "description": "Create or overwrite a file in the Opsora workspace.",
        "parameters": {"path": "str", "content": "str", "append": "bool = false"},
        "fn": write_file,
    },
    {
        "name": "run_local_command",
        "description": "Run a shell command on the API host (terminal). Destructive commands require approval.",
        "parameters": {"command": "str", "cwd": "str | None"},
        "fn": run_local_command,
    },
    {
        "name": "github_run",
        "description": "Run GitHub CLI (gh) — repos, PRs, issues, actions. Requires GITHUB_TOKEN.",
        "parameters": {"command": "str"},
        "fn": github_run,
    },
    {
        "name": "github_api",
        "description": "GitHub REST API call. Path like /repos/owner/repo or /user/repos.",
        "parameters": {"method": "str", "path": "str", "body": "dict | None"},
        "fn": github_api,
    },
    {
        "name": "mcp_invoke",
        "description": "Invoke MCP server: terminal (shell), github (gh/api), or custom HTTP MCP.",
        "parameters": {"server": "str", "tool": "str", "arguments": "dict"},
        "fn": mcp_invoke,
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
