"""LangGraph-compatible agent tools. Real implementations wired to the SSH pool & provider adapters."""
from __future__ import annotations

import json
from typing import Any

from app.core.db import SessionLocal
from app.models.models import Instance
from app.services.ssh_pool import ssh_pool
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
    from app.services.providers.vultr import get_adapter
    adapter = get_adapter(provider, **(spec.get("adapter_kwargs", {})))
    return adapter.create_instance(spec)


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
