"""LangGraph-based agent planner for Opsora Agent."""
from __future__ import annotations

import json
from typing import Any, AsyncIterator

from app.agent.tools import call_tool, tools_json
from app.core.config import settings


def _llm_client() -> Any:
    from openai import AsyncOpenAI
    return AsyncOpenAI(api_key=settings.LLM_API_KEY or "dummy", base_url=settings.LLM_BASE_URL)


AgentState = dict[str, Any]


async def _llm_json(client: Any, system: str, user: str) -> Any:
    resp = await client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.2,
    )
    content = resp.choices[0].message.content or ""
    if content.startswith("```"):
        content = content.strip("`").lstrip("json").strip()
    try:
        return json.loads(content)
    except Exception:
        return {"_raw": content}


async def _llm_text(client: Any, system: str, user: str) -> str:
    resp = await client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.3,
        max_tokens=1024,
    )
    return (resp.choices[0].message.content or "").strip()


async def plan_node(state: AgentState) -> AgentState:
    client = _llm_client()
    system = (
        "You are Opsora Agent, an autonomous coding and infrastructure assistant. "
        "Decompose the user's goal into a JSON list of steps. "
        'Each step is {"tool": <name>, "args": {<kwargs>}}. Available tools:\n'
        + json.dumps(tools_json())
    )
    plan = await _llm_json(client, system, f"Goal: {state['goal']}\nReturn JSON list of steps.")
    if isinstance(plan, dict) and "_raw" in plan:
        plan = [{"tool": "list_files", "args": {"path": ""}}]
    state["plan"] = plan if isinstance(plan, list) else [plan]
    state["step_index"] = 0
    state["executed"] = []
    return state


async def execute_node(state: AgentState) -> AgentState:
    idx = state.get("step_index", 0)
    plan = state.get("plan", [])
    if idx >= len(plan):
        state["status"] = "done"
        return state
    step = plan[idx]
    tool = step.get("tool", "")
    args = step.get("args", {}) or {}
    result = await call_tool(tool, **args)
    state["executed"].append({"step": idx, "tool": tool, "args": args, "result": result})
    state["step_index"] = idx + 1
    return state


async def reflect_node(state: AgentState) -> AgentState:
    if state["step_index"] >= len(state["plan"]):
        state["status"] = "done"
        return state
    client = _llm_client()
    system = (
        "You are Opsora Agent. Decide whether the goal is achieved given executed steps. "
        'Reply JSON {"status": "done" | "continue" | "fail", "reason": "..."}.'
    )
    user = json.dumps({"goal": state["goal"], "executed": state["executed"][:8]})
    try:
        verdict = await _llm_json(client, system, user)
    except Exception:
        verdict = {"status": "continue"}
    s = verdict.get("status", "continue") if isinstance(verdict, dict) else "continue"
    if s in ("done", "fail"):
        state["status"] = s if s == "done" else "failed"
    else:
        state["status"] = "running"
    return state


async def synthesize_response(goal: str, executed: list[dict[str, Any]]) -> str:
    client = _llm_client()
    system = (
        "You are Opsora Agent. Summarize what was done and answer the user clearly. "
        "Use Indonesian if the user wrote in Indonesian. Be concise and actionable."
    )
    user = json.dumps({"goal": goal, "executed": executed[:10]}, ensure_ascii=False)
    try:
        return await _llm_text(client, system, user)
    except Exception:
        if not executed:
            return "Saya tidak dapat menyelesaikan tugas ini saat ini."
        return f"Selesai menjalankan {len(executed)} langkah untuk: {goal}"


async def run_agent(goal: str) -> AsyncIterator[dict[str, Any]]:
    """Stream plan → step → message → done events."""
    state: AgentState = {"goal": goal, "status": "running", "executed": []}
    state = await plan_node(state)
    yield {"type": "plan", "plan": state["plan"]}

    while state.get("status") not in ("done", "failed") and state["step_index"] < len(state["plan"]):
        state = await execute_node(state)
        last = state["executed"][-1]
        yield {
            "type": "step",
            "step": last["step"],
            "tool": last["tool"],
            "args": last["args"],
            "result": last["result"],
        }
        state = await reflect_node(state)

    if state.get("status") != "failed":
        state["status"] = "done"

    message = await synthesize_response(goal, state.get("executed", []))
    yield {"type": "message", "content": message}
    yield {"type": "done", "status": state["status"], "response": message}


async def run_agent_sync(goal: str) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    async for ev in run_agent(goal):
        events.append(ev)
    return {
        "events": events,
        "final_status": events[-1].get("status") if events else "failed",
        "response": next((e.get("content") for e in reversed(events) if e.get("type") == "message"), ""),
    }
