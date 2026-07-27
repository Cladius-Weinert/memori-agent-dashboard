"""Cursor-style agent loop — plan → tool → reflect until goal is done."""
from __future__ import annotations

import json
import os
import re
from typing import Any, AsyncIterator

from openai import AsyncOpenAI

from app.agent.tools import TOOLS, call_tool, tools_json
from app.core.config import settings

MAX_TOOL_ITERATIONS = 12
EXECUTOR_MODEL = "meta/llama-3.1-70b-instruct"
ORCHESTRATOR_MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
FALLBACK_MODEL = "meta/llama-3.1-70b-instruct"

TOOL_SYSTEM = """You are the Opsora EXECUTOR agent in a tool loop (like Cursor).
Given a goal and prior tool results, decide the NEXT action.

Available tools:
""" + json.dumps([{"name": t["name"], "description": t["description"], "parameters": t["parameters"]} for t in TOOLS], indent=2) + """

Output ONLY valid JSON (one object):
{"action":"tool","tool":"<name>","args":{...},"reason":"why this step"}
OR when goal is satisfied:
{"action":"done","summary":"what was accomplished","reason":"why done"}
OR if stuck:
{"action":"fail","reason":"what blocked progress"}

Rules:
- Prefer webfetch for docs/URLs, read_file/write_file for code, run_local_command for terminal.
- Use list_instances/run_command for remote servers.
- One tool per step. Be specific in args."""

REFLECT_SYSTEM = """You judge whether an Opsora agent goal is complete.
Reply ONLY JSON: {"complete": true|false, "reason": "..."}"""


def _client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.LLM_API_KEY or os.getenv("NVIDIA_API_KEY", ""),
        base_url=settings.LLM_BASE_URL,
        timeout=120,
    )


def _strip_json(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"action": "fail", "reason": f"invalid JSON: {text[:200]}"}


async def _llm(model: str, system: str, user: str, *, max_tokens: int = 1024) -> tuple[str, str]:
    client = _client()
    try:
        resp = await client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.25,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or "", model
    except Exception:
        if model != FALLBACK_MODEL:
            resp = await client.chat.completions.create(
                model=FALLBACK_MODEL,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.25,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content or "", FALLBACK_MODEL
        raise


def _goal_needs_tools(goal: str, mode: str, plan: list[str] | None = None) -> bool:
    g = goal.lower()
    keywords = (
        "fetch", "web", "http", "url", "file", "create", "write", "build",
        "run ", "terminal", "command", "deploy", "status", "health", "search",
        "debug", "fix", "code", "server", "instance", "log",
    )
    if mode in ("plan", "research"):
        return True
    if any(k in g for k in keywords):
        return True
    if plan:
        plan_text = " ".join(str(p) for p in plan).lower()
        if any(k in plan_text for k in keywords):
            return True
    return False


async def run_tool_loop(
    goal: str,
    *,
    mode: str = "chat",
    plan: list[str] | None = None,
    done_criteria: str = "",
    context: list[str] | None = None,
    max_iterations: int = MAX_TOOL_ITERATIONS,
    auto_approve: bool = False,
) -> AsyncIterator[dict[str, Any]]:
    """Execute tools in a loop until done, fail, or max iterations."""
    if not _goal_needs_tools(goal, mode, plan):
        return

    executed: list[dict[str, Any]] = []
    ctx = list(context or [])
    if plan:
        ctx.append("Plan:\n" + "\n".join(f"- {s}" for s in plan))
    if done_criteria:
        ctx.append(f"Done criteria: {done_criteria}")

    yield {
        "type": "loop_start",
        "max_iterations": max_iterations,
        "tools": [t["name"] for t in TOOLS],
    }

    for iteration in range(1, max_iterations + 1):
        history = json.dumps(executed[-6:], default=str)[:6000]
        user_msg = (
            f"Goal: {goal}\nMode: {mode}\nIteration: {iteration}/{max_iterations}\n\n"
            f"Context:\n" + "\n".join(ctx[-8:]) + f"\n\nExecuted so far:\n{history}"
        )

        raw, model = await _llm(EXECUTOR_MODEL, TOOL_SYSTEM, user_msg, max_tokens=800)
        decision = _strip_json(raw)
        if not isinstance(decision, dict):
            decision = {"action": "fail", "reason": "bad decision format"}

        action = decision.get("action", "fail")

        if action == "done":
            yield {
                "type": "loop_reflect",
                "iteration": iteration,
                "status": "done",
                "reason": decision.get("reason", ""),
                "summary": decision.get("summary", ""),
                "model": model,
            }
            yield {
                "type": "loop_done",
                "status": "done",
                "summary": decision.get("summary", decision.get("reason", "")),
                "executed": executed,
                "iterations": iteration,
            }
            return

        if action == "fail":
            yield {
                "type": "loop_done",
                "status": "failed",
                "summary": decision.get("reason", "agent gave up"),
                "executed": executed,
                "iterations": iteration,
            }
            return

        tool_name = decision.get("tool", "")
        args = decision.get("args", {}) or {}
        if not isinstance(args, dict):
            args = {}

        yield {
            "type": "tool_start",
            "iteration": iteration,
            "tool": tool_name,
            "args": args,
            "reason": decision.get("reason", ""),
            "model": model,
        }

        result = await call_tool(tool_name, **args)
        entry = {"iteration": iteration, "tool": tool_name, "args": args, "result": result}
        executed.append(entry)

        if result.get("requires_approval") and not auto_approve:
            yield {
                "type": "approval_required",
                "iteration": iteration,
                "tool": tool_name,
                "args": args,
                "result": result,
            }
            yield {
                "type": "loop_done",
                "status": "approval_required",
                "summary": result.get("warning", "approval needed"),
                "executed": executed,
                "iterations": iteration,
            }
            return

        yield {
            "type": "tool_done",
            "iteration": iteration,
            "tool": tool_name,
            "args": args,
            "result": _truncate_result(result),
        }

        # Quick reflect every 3 steps or on last iteration
        if iteration % 3 == 0 or iteration == max_iterations:
            reflect_user = json.dumps({
                "goal": goal,
                "done_criteria": done_criteria,
                "executed": executed[-4:],
            }, default=str)[:4000]
            reflect_raw, _ = await _llm(ORCHESTRATOR_MODEL, REFLECT_SYSTEM, reflect_user, max_tokens=256)
            verdict = _strip_json(reflect_raw)
            complete = isinstance(verdict, dict) and verdict.get("complete") is True
            yield {
                "type": "loop_reflect",
                "iteration": iteration,
                "status": "done" if complete else "continue",
                "reason": verdict.get("reason", "") if isinstance(verdict, dict) else "",
            }
            if complete:
                yield {
                    "type": "loop_done",
                    "status": "done",
                    "summary": verdict.get("reason", "goal complete") if isinstance(verdict, dict) else "",
                    "executed": executed,
                    "iterations": iteration,
                }
                return

    yield {
        "type": "loop_done",
        "status": "max_iterations",
        "summary": f"reached {max_iterations} tool steps",
        "executed": executed,
        "iterations": max_iterations,
    }


def _truncate_result(result: dict[str, Any], limit: int = 1200) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in result.items():
        if isinstance(v, str) and len(v) > limit:
            out[k] = v[:limit] + "…"
        else:
            out[k] = v
    return out
