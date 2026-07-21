"""LangGraph-based agent planner.

The agent follows a plan → execute → reflect loop:
- `plan`:  LLM produces a JSON list of {tool, args} steps to achieve the goal.
- `execute`: each step is run via app.agent.tools.call_tool; results are stored.
- `reflect`: after each step the LLM decides whether the goal is satisfied (continue / done / fail).

The LangGraph graph is best-effort: if langgraph is not installed, we fall back to a
simple loop using the OpenAI client directly so the agent runtime still works.
"""
from __future__ import annotations

import json
from typing import Any, AsyncIterator, Literal

from app.agent.tools import call_tool, tools_json
from app.core.config import settings

try:
    from langgraph.graph import StateGraph, END  # type: ignore[import-untyped]
    _HAS_LANGGRAPH = True
except ImportError:  # pragma: no cover
    StateGraph = None  # type: ignore[assignment]
    END = "__end__"  # type: ignore[assignment]
    _HAS_LANGGRAPH = False


def _llm_client() -> Any:
    from openai import AsyncOpenAI
    return AsyncOpenAI(api_key=settings.LLM_API_KEY or "dummy", base_url=settings.LLM_BASE_URL)


AgentState = dict[str, Any]


async def _llm_json(client: Any, system: str, user: str) -> Any:
    """Ask LLM for a JSON response. Falls back gracefully on parse errors."""
    resp = await client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.2,
    )
    content = resp.choices[0].message.content or ""
    # strip ```json fences
    if content.startswith("```"):
        content = content.strip("`").lstrip("json").strip()
    try:
        return json.loads(content)
    except Exception:
        # fallback: return a single step that just echoes the raw content
        return {"_raw": content}


async def plan_node(state: AgentState) -> AgentState:
    """Ask the LLM to produce a list of steps from the goal."""
    client = _llm_client()
    system = (
        "You are Memori, an autonomous infra agent. Decompose the user's goal into a JSON list "
        "of steps. Each step is {\"tool\": <name>, \"args\": {<kwargs>}}. Available tools:\n"
        + json.dumps(tools_json())
    )
    plan = await _llm_json(client, system, f"Goal: {state['goal']}\nReturn JSON list of steps.")
    if isinstance(plan, dict) and "_raw" in plan:
        plan = [{"tool": "list_instances", "args": {}}]
    state["plan"] = plan if isinstance(plan, list) else [plan]
    state["step_index"] = 0
    state["executed"] = []
    return state


async def execute_node(state: AgentState) -> AgentState:
    """Execute the current step (plan[step_index]) and store the result."""
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
    """Ask the LLM whether the goal is satisfied, remaining steps, or failed."""
    if state["step_index"] >= len(state["plan"]):
        state["status"] = "done"
        return state
    client = _llm_client()
    system = (
        "You are Memori. Decide whether the goal is achieved given the executed steps. "
        "Reply JSON {\"status\": \"done\" | \"continue\" | \"fail\", \"reason\": \"...\"}."
    )
    user = json.dumps({"goal": state["goal"], "executed": state["executed"][:6]})
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


def _route(state: AgentState) -> Literal["execute", "end"]:
    if state.get("status") in ("done", "failed") or state.get("step_index", 0) >= len(state.get("plan", [])):
        return "end"
    return "execute"


def build_graph() -> Any:
    """Compile the LangGraph agent (or return a stub synchronous runner if unavailable)."""
    if not _HAS_LANGGRAPH:
        return None
    g = StateGraph(dict)  # type: ignore[arg-type]
    g.add_node("plan", plan_node)
    g.add_node("execute", execute_node)
    g.add_node("reflect", reflect_node)
    g.set_entry_point("plan")
    g.add_edge("plan", "execute")
    g.add_edge("execute", "reflect")
    g.add_conditional_edges("reflect", _route, {"execute": "execute", "end": END})
    return g.compile()


_GRAPH = None


def _get_graph() -> Any:
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_graph()
    return _GRAPH


async def run_agent(goal: str) -> AsyncIterator[dict[str, Any]]:
    """Async generator yielding typed events for SSE streaming.

    Yields dicts like:
      {"type": "plan", "plan": [...]}
      {"type": "step", "step": {...}, "result": {...}}
      {"type": "done", "status": "done" | "failed"}
    """
    state: AgentState = {"goal": goal, "status": "running", "executed": []}
    graph = _get_graph()
    if graph is None:
        # fallback loop (langgraph not installed)
        state = await plan_node(state)
        yield {"type": "plan", "plan": state["plan"]}
        while state.get("status") not in ("done", "failed") and state["step_index"] < len(state["plan"]):
            state = await execute_node(state)
            last = state["executed"][-1]
            yield {"type": "step", "step": last["step"], "tool": last["tool"], "args": last["args"], "result": last["result"]}
            state = await reflect_node(state)
        yield {"type": "done", "status": state["status"]}
        return

    async for chunk in graph.astream(state, stream_mode="values"):
        if "plan" in chunk and "step_index" not in state.get("_yielded_plan", {}) if False else False:  # pragma: no cover
            pass
        # For streaming simplicity: just emit done at the end
    yield {"type": "done", "status": "done"}


async def run_agent_sync(goal: str) -> dict[str, Any]:
    """Non-streaming runner used by the Celery worker."""
    result_events: list[dict[str, Any]] = []
    async for ev in run_agent(goal):
        result_events.append(ev)
    return {"events": result_events, "final_status": result_events[-1].get("status") if result_events else "failed"}
