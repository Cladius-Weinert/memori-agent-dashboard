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

TOOL_SYSTEM = """You are Opsora — a global AI agent (Cursor-style tool loop).
You help with ANY task: coding, research, writing, planning, infra, GitHub, web, files, todos — not only console/server work.

Available tools:
""" + json.dumps([{"name": t["name"], "description": t["description"], "parameters": t["parameters"]} for t in TOOLS], indent=2) + """

Output ONLY valid JSON (one object):
{"action":"tool","tool":"<name>","args":{...},"reason":"short why"}
OR when goal is satisfied:
{"action":"done","summary":"clear user-facing answer of what was done / the result","reason":"why done"}
OR if stuck:
{"action":"fail","reason":"what blocked progress"}

Rules:
- Prefer webfetch for docs/URLs; read_file/write_file for code; run_local_command for shell; github_* for GitHub.
- Use todo_create with titles=[] for multi-step checklists.
- For pure Q&A with no side effects, prefer action=done with a useful summary (do not force tools).
- One tool per step. Be specific in args. Keep reason short."""

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
        # try extract first {...}
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
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
        "debug", "fix", "code", "server", "instance", "log", "github", "gh ",
        "repo", "pull request", "pr ", "commit", "git ",
        "todo", "todos", "checklist", "tugas", "daftar",
        "install", "update", "hapus", "delete", "cek ", "check ", "list ",
        "baca", "read ", "unduh", "download", "upload", "analisis file",
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
    executor_model: str | None = None,
    reflect_model: str | None = None,
    force: bool = False,
) -> AsyncIterator[dict[str, Any]]:
    """Execute tools in a loop until done, fail, or max iterations."""
    exec_model = executor_model or EXECUTOR_MODEL
    refl_model = reflect_model or ORCHESTRATOR_MODEL

    if not force and not _goal_needs_tools(goal, mode, plan):
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

        raw, model = await _llm(exec_model, TOOL_SYSTEM, user_msg, max_tokens=800)
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
        yield {
            "type": "activity",
            "kind": "tool",
            "status": "running",
            "text": tool_name,
            "detail": decision.get("reason", ""),
            "key": f"tool-{iteration}-{tool_name}",
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
        yield {
            "type": "activity",
            "kind": "tool",
            "status": "done",
            "text": tool_name,
            "detail": _activity_detail(result),
            "key": f"tool-{iteration}-{tool_name}",
            "output": _activity_detail(result),
        }
        for line in _repl_lines(result):
            yield {"type": "activity", "kind": "repl", "status": "done", "text": line}
            yield {"type": "repl_line", "text": line}

        # Quick reflect every 3 steps or on last iteration
        if iteration % 3 == 0 or iteration == max_iterations:
            reflect_user = json.dumps({
                "goal": goal,
                "done_criteria": done_criteria,
                "executed": executed[-4:],
            }, default=str)[:4000]
            reflect_raw, _ = await _llm(refl_model, REFLECT_SYSTEM, reflect_user, max_tokens=256)
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


CHAT_SYSTEM = """You are Opsora — a global AI assistant and agent.
Help with anything: coding, writing, research, planning, cloud/infra, GitHub, product questions, and everyday tasks.
Be concise, actionable, and clear. Use markdown sparingly. Prefer Indonesian if the user writes in Indonesian."""


async def run_single_model_agent(
    goal: str,
    *,
    model: str,
    mode: str = "chat",
    history: list[dict[str, str]] | None = None,
    max_iterations: int = MAX_TOOL_ITERATIONS,
    force_loop: bool = False,
) -> AsyncIterator[dict[str, Any]]:
    """Single-model agent: tool loop when needed, otherwise direct chat."""
    # Never run the tool loop on reasoning-only models
    from app.services.user_config import _sanitize_loop_model
    model = _sanitize_loop_model(model)

    needs_tools = force_loop or _goal_needs_tools(goal, mode)

    yield {
        "type": "activity",
        "kind": "thinking",
        "status": "running",
        "text": "Thinking",
        "detail": model.split("/")[-1],
        "key": "thinking",
    }

    if needs_tools:
        reply_parts: list[str] = []
        async for ev in run_tool_loop(
            goal,
            mode=mode,
            max_iterations=max_iterations,
            executor_model=model,
            reflect_model=FALLBACK_MODEL,
            force=force_loop,
        ):
            if ev.get("type") == "loop_start":
                yield {
                    "type": "activity",
                    "kind": "thinking",
                    "status": "done",
                    "text": "Planning",
                    "detail": f"{ev.get('max_iterations', 12)} steps max",
                    "key": "thinking",
                }
            yield ev
            if ev.get("type") == "loop_done":
                reply_parts.append(str(ev.get("summary", "")))
        summary = reply_parts[-1] if reply_parts else "Selesai."
        yield {"type": "done", "reply": summary, "plan": [], "loops": 1, "model": model}
        return

    client = _client()
    mode_extra = {
        "plan": " Focus on a clear numbered plan.",
        "research": " Research from multiple angles and summarize findings.",
    }.get(mode, "")
    messages: list[dict[str, str]] = [{"role": "system", "content": CHAT_SYSTEM + mode_extra}]
    for h in (history or [])[-10:]:
        if h.get("role") in ("user", "assistant") and h.get("content"):
            messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": goal})

    try:
        resp = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.4,
            max_tokens=2048,
        )
        reply = resp.choices[0].message.content or ""
    except Exception as exc:
        # fallback once
        try:
            resp = await client.chat.completions.create(
                model=FALLBACK_MODEL,
                messages=messages,
                temperature=0.4,
                max_tokens=2048,
            )
            reply = resp.choices[0].message.content or ""
            model = FALLBACK_MODEL
        except Exception:
            reply = f"Error: {exc}"

    yield {
        "type": "activity",
        "kind": "thinking",
        "status": "done",
        "text": "Thinking",
        "detail": model.split("/")[-1],
        "key": "thinking",
    }
    yield {"type": "done", "reply": reply, "plan": [], "loops": 0, "model": model}


def _truncate_result(result: dict[str, Any], limit: int = 1200) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in result.items():
        if isinstance(v, str) and len(v) > limit:
            out[k] = v[:limit] + "…"
        else:
            out[k] = v
    return out


def _activity_detail(result: dict[str, Any]) -> str:
    if result.get("error"):
        return str(result["error"])[:200]
    if result.get("stdout"):
        return str(result["stdout"])[:120]
    if result.get("body"):
        return str(result["body"])[:120]
    return ""


def _repl_lines(result: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for key in ("stdout", "stderr", "body"):
        val = result.get(key)
        if isinstance(val, str) and val.strip():
            for ln in val.strip().split("\n")[:12]:
                prefix = "$ " if key == "stdout" else ("! " if key == "stderr" else "> ")
                lines.append(f"{prefix}{ln[:200]}")
    if result.get("exit_code") is not None:
        lines.append(f"exit {result['exit_code']}")
    return lines
