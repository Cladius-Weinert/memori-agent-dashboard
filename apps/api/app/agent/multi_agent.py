"""NVIDIA multi-agent orchestrator — routes tasks to specialized models.

Agent roles (mapped to available NVIDIA NIM models):
  orchestrator  → nvidia/nemotron-3-nano-omni-30b-a3b-reasoning  (plan, route, loop)
  visual        → meta/llama-3.2-90b-vision-instruct             (UI/layout/design)
  executor      → meta/llama-3.1-70b-instruct                    (chat, tools, code)
  deep          → deepseek-ai/deepseek-v4-pro                     (complex reasoning, fallback 70b)
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator

from openai import AsyncOpenAI

from app.core.config import settings
from app.agent.agent_loop import run_tool_loop, _goal_needs_tools

# ── Model registry (verified on account) ────────────────────────

class AgentRole(str, Enum):
    ORCHESTRATOR = "orchestrator"
    VISUAL = "visual"
    EXECUTOR = "executor"
    DEEP = "deep"
    EXPLORE = "explore"


AGENT_MODELS: dict[AgentRole, str] = {
    AgentRole.ORCHESTRATOR: "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
    AgentRole.VISUAL: "meta/llama-3.2-90b-vision-instruct",
    AgentRole.EXECUTOR: "meta/llama-3.1-70b-instruct",
    AgentRole.DEEP: "deepseek-ai/deepseek-v4-pro",
    AgentRole.EXPLORE: "meta/llama-3.1-70b-instruct",
}

AGENT_LABELS: dict[AgentRole, str] = {
    AgentRole.ORCHESTRATOR: "ORCH",
    AgentRole.VISUAL: "VISUAL",
    AgentRole.EXECUTOR: "GENERAL",
    AgentRole.DEEP: "DEEP",
    AgentRole.EXPLORE: "EXPLORE",
}

FALLBACK_MODEL = "meta/llama-3.1-70b-instruct"
MAX_LOOPS = 8


@dataclass
class AgentStep:
    agent: AgentRole
    status: str  # running | done | failed
    output: str = ""
    tool: str | None = None
    model: str = ""


@dataclass
class MultiAgentState:
    goal: str
    mode: str = "chat"
    steps: list[AgentStep] = field(default_factory=list)
    plan: list[str] = field(default_factory=list)
    done: bool = False
    final_reply: str = ""
    loop_count: int = 0
    requires_tools: bool = False
    done_criteria: str = ""
    tool_executed: list[dict[str, Any]] = field(default_factory=list)
    tool_summary: str = ""


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
        return {"raw": text}


async def _call_agent(
    role: AgentRole,
    system: str,
    user: str,
    *,
    max_tokens: int = 2048,
    models: dict[AgentRole, str] | None = None,
) -> tuple[str, str]:
    """Returns (content, model_used)."""
    client = _client()
    registry = models or AGENT_MODELS
    model = registry.get(role, AGENT_MODELS.get(role, FALLBACK_MODEL))
    try:
        resp = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.35,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or "", model
    except Exception:
        if model != FALLBACK_MODEL:
            resp = await client.chat.completions.create(
                model=FALLBACK_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.35,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content or "", FALLBACK_MODEL
        raise


def _classify_goal(goal: str, mode: str) -> list[AgentRole]:
    """Route which agents participate based on goal + mode."""
    g = goal.lower()
    agents: list[AgentRole] = [AgentRole.ORCHESTRATOR]

    if mode == "plan" or any(k in g for k in ("deploy", "plan", "step", "architecture", "design ui", "tampilan")):
        agents.append(AgentRole.VISUAL)
    if any(k in g for k in ("debug", "error", "fix", "bug", "code")):
        agents.append(AgentRole.DEEP)
    if any(k in g for k in ("search", "explore", "list", "status", "health", "audit")):
        agents.append(AgentRole.EXPLORE)

    agents.append(AgentRole.EXECUTOR)
    # dedupe preserving order
    seen: set[AgentRole] = set()
    out: list[AgentRole] = []
    for a in agents:
        if a not in seen:
            seen.add(a)
            out.append(a)
    return out


ORCHESTRATOR_SYSTEM = """You are the Opsora ORCHESTRATOR agent (NVIDIA Nemotron Reasoning).
Decompose the user goal into a JSON plan the team can execute.
Output ONLY valid JSON:
{"goal_summary":"...","steps":["step1","step2"],"agents_needed":["visual","executor"],"done_criteria":"...","requires_tools":true}
Set requires_tools=true when the goal needs webfetch, files, terminal, github, or cloud ops.
Loop until done_criteria met. Be specific: use run_local_command for shell, github_run for repos/PRs, mcp_invoke for MCP servers."""

VISUAL_SYSTEM = """You are the Opsora VISUAL agent (Llama 90B Vision).
When asked about UI, layout, or design — output structured design guidance:
colors, component placement, hierarchy, multi-agent panel layout.
Industrial dark ops aesthetic. NVIDIA green #76b900. NOT generic purple AI slop.
Be concrete: spacing, font sizes, panel structure."""

EXECUTOR_SYSTEM = """You are the Opsora EXECUTOR agent (Llama 70B).
Synthesize the orchestrator plan and specialist outputs into a clear, actionable reply for the user.
Execute tasks using tools: run_local_command (terminal), github_run/github_api, mcp_invoke, webfetch.
If plan incomplete, say what's next. Be concise."""

DEEP_SYSTEM = """You are the Opsora DEEP reasoning agent (DeepSeek).
Analyze complex bugs, architecture, security. Step-by-step reasoning.
Output root cause + fix recommendation."""

EXPLORE_SYSTEM = """You are the Opsora EXPLORE agent.
Quickly scan and summarize: server status, MCP tools, cloud resources, codebase structure.
Be fast and factual."""


async def run_multi_agent(
    goal: str,
    mode: str = "chat",
    history: list[dict[str, str]] | None = None,
    user_id: int | None = None,
    custom_models: dict[str, str] | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Yield SSE-style events as each NVIDIA sub-agent runs."""
    from app.agent.tools import set_tool_user
    set_tool_user(user_id)
    models: dict[AgentRole, str] = dict(AGENT_MODELS)
    if custom_models:
        for role in AgentRole:
            if role.value in custom_models:
                models[role] = custom_models[role.value]
    state = MultiAgentState(goal=goal, mode=mode)
    agents = _classify_goal(goal, mode)
    context_parts: list[str] = []

    if history:
        context_parts.append("History:\n" + "\n".join(f"{h['role']}: {h['content'][:200]}" for h in history[-5:]))

    yield {"type": "agents", "agents": [{"role": a.value, "label": AGENT_LABELS[a], "model": models[a]} for a in agents]}

    orchestrator_done = False
    while state.loop_count < MAX_LOOPS and not state.done:
        state.loop_count += 1

        for role in agents:
            if role == AgentRole.ORCHESTRATOR and orchestrator_done:
                continue
            step = AgentStep(agent=role, status="running", model=models[role])
            state.steps.append(step)
            yield {
                "type": "agent_start",
                "agent": role.value,
                "label": AGENT_LABELS[role],
                "model": models[role],
                "loop": state.loop_count,
            }
            yield {
                "type": "activity",
                "kind": "agent",
                "status": "running",
                "text": AGENT_LABELS[role],
                "detail": models[role].split("/")[-1],
            }

            ctx = "\n".join(context_parts)
            user_msg = f"Goal: {goal}\nMode: {mode}\n\n{ctx}"

            if role == AgentRole.ORCHESTRATOR:
                content, model = await _call_agent(role, ORCHESTRATOR_SYSTEM, user_msg, max_tokens=1024, models=models)
                parsed = _strip_json(content)
                if isinstance(parsed, dict) and "steps" in parsed:
                    state.plan = parsed.get("steps", [])
                    state.done_criteria = parsed.get("done_criteria", "")
                    state.requires_tools = bool(parsed.get("requires_tools", True))
                    orchestrator_done = True
                step.output = content
            elif role == AgentRole.VISUAL:
                content, model = await _call_agent(role, VISUAL_SYSTEM, user_msg, max_tokens=1500, models=models)
                step.output = content
            elif role == AgentRole.DEEP:
                content, model = await _call_agent(role, DEEP_SYSTEM, user_msg, max_tokens=1500, models=models)
                step.output = content
            elif role == AgentRole.EXPLORE:
                content, model = await _call_agent(role, EXPLORE_SYSTEM, user_msg, max_tokens=800, models=models)
                step.output = content
            else:
                tool_ctx = ""
                if state.tool_executed:
                    tool_ctx = "\n\nTool results:\n" + json.dumps(state.tool_executed[-6:], default=str)[:4000]
                    if state.tool_summary:
                        tool_ctx += f"\n\nTool loop summary: {state.tool_summary}"
                synth_ctx = ctx + tool_ctx + "\n\nSpecialist outputs:\n" + "\n---\n".join(
                    f"[{s.agent.value}]: {s.output[:500]}" for s in state.steps if s.output
                )
                content, model = await _call_agent(role, EXECUTOR_SYSTEM, f"Goal: {goal}\n\n{synth_ctx}", max_tokens=2048, models=models)
                step.output = content
                state.final_reply = content

            step.status = "done"
            step.model = model
            context_parts.append(f"[{role.value}]: {step.output[:600]}")
            yield {
                "type": "agent_done",
                "agent": role.value,
                "label": AGENT_LABELS[role],
                "model": model,
                "output": step.output[:800],
                "plan": state.plan,
            }
            yield {
                "type": "activity",
                "kind": "agent",
                "status": "done",
                "text": AGENT_LABELS[role],
                "detail": step.output[:160],
            }

        # Tool loop after first orchestration pass
        if orchestrator_done and (state.requires_tools or _goal_needs_tools(goal, mode, state.plan)) and not state.tool_executed:
            async for ev in run_tool_loop(
                goal,
                mode=mode,
                plan=state.plan,
                done_criteria=state.done_criteria,
                context=context_parts,
            ):
                yield ev
                if ev.get("type") == "tool_done":
                    state.tool_executed.append({
                        "tool": ev.get("tool"),
                        "args": ev.get("args"),
                        "result": ev.get("result"),
                    })
                elif ev.get("type") == "loop_done":
                    state.tool_summary = ev.get("summary", "")
                    if ev.get("executed"):
                        state.tool_executed = ev["executed"]

            # Re-run executor with tool results
            if state.tool_executed:
                synth = "\n".join(context_parts)
                tool_blob = json.dumps(state.tool_executed[-8:], default=str)[:5000]
                final_content, final_model = await _call_agent(
                    AgentRole.EXECUTOR,
                    EXECUTOR_SYSTEM,
                    f"Goal: {goal}\n\n{synth}\n\nTool execution results:\n{tool_blob}\n\nSummarize outcomes for the user.",
                    max_tokens=2048,
                    models=models,
                )
                state.final_reply = final_content
                yield {
                    "type": "agent_done",
                    "agent": AgentRole.EXECUTOR.value,
                    "label": AGENT_LABELS[AgentRole.EXECUTOR],
                    "model": final_model,
                    "output": final_content[:800],
                    "plan": state.plan,
                }

        if state.final_reply:
            state.done = True

    yield {
        "type": "done",
        "reply": state.final_reply or (state.steps[-1].output if state.steps else ""),
        "plan": state.plan,
        "loops": state.loop_count,
        "agents_used": [s.agent.value for s in state.steps],
        "tools_executed": len(state.tool_executed),
        "tool_summary": state.tool_summary,
    }
