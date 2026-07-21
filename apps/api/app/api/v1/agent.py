"""Agent run + SSE stream endpoints."""
from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.models import AgentAction, AgentJob, User
from app.schemas import AgentJobRead, AgentRunIn
from app.agent.planner import run_agent, run_agent_sync
from app.api.v1.auth import get_current_user

router = APIRouter()


@router.post("/run", response_model=AgentJobRead, status_code=201)
async def run_agent_job(
    data: AgentRunIn,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AgentJob:
    job = AgentJob(user_id=current_user.id, goal=data.goal, status="planning")
    session.add(job)
    await session.commit()
    await session.refresh(job)

    asyncio.create_task(_run_agent_background(job.id, data.goal))
    return job


async def _run_agent_background(job_id: int, goal: str) -> None:
    from app.core.db import SessionLocal
    async with SessionLocal() as session:
        job = await session.get(AgentJob, job_id)
        if not job:
            return
        job.status = "running"
        await session.commit()

        async for ev in run_agent(goal):
            ev_type = ev.get("type")
            if ev_type == "plan":
                job.plan = ev.get("plan", [])
            elif ev_type == "step":
                action = AgentAction(
                    job_id=job_id,
                    tool=ev.get("tool", ""),
                    params=ev.get("args", {}),
                    result=ev.get("result", {}),
                    requires_approval=ev.get("result", {}).get("requires_approval", False),
                )
                session.add(action)
            elif ev_type == "done":
                job.status = ev.get("status", "done")
            await session.commit()


@router.get("/jobs/{job_id}", response_model=AgentJobRead)
async def get_agent_job(job_id: int, session: AsyncSession = Depends(get_db)) -> AgentJob:
    job = await session.get(AgentJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="agent job not found")
    return job


@router.get("/jobs/{job_id}/stream")
async def stream_agent_job(job_id: int, session: AsyncSession = Depends(get_db)) -> StreamingResponse:
    """SSE stream of agent execution events."""
    job = await session.get(AgentJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="agent job not found")

    async def event_generator() -> AsyncIterator[str]:
        from app.core.db import SessionLocal
        last_action_count = 0
        while True:
            async with SessionLocal() as s:
                j = await s.get(AgentJob, job_id)
                if not j:
                    break

                actions = (await s.execute(
                    select(AgentAction).where(AgentAction.job_id == job_id).order_by(AgentAction.id)
                )).scalars().all()

                if j.plan and last_action_count == 0:
                    yield f"data: {json.dumps({'type': 'plan', 'plan': j.plan})}\n\n"

                for i, a in enumerate(actions):
                    if i >= last_action_count:
                        yield f"data: {json.dumps({'type': 'step', 'step': i, 'tool': a.tool, 'params': a.params, 'result': a.result or {}, 'requires_approval': a.requires_approval})}\n\n"

                last_action_count = len(actions)

                if j.status in ("done", "completed", "failed"):
                    yield f"data: {json.dumps({'type': 'done', 'status': j.status})}\n\n"
                    break

            await asyncio.sleep(1.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/actions")
async def list_actions(
    job_id: int = Query(...),
    session: AsyncSession = Depends(get_db),
) -> list[dict]:
    actions = (await session.execute(
        select(AgentAction).where(AgentAction.job_id == job_id).order_by(AgentAction.id)
    )).scalars().all()
    return [
        {
            "id": a.id,
            "job_id": a.job_id,
            "tool": a.tool,
            "params": a.params,
            "result": a.result,
            "requires_approval": a.requires_approval,
            "approved_by": a.approved_by,
        }
        for a in actions
    ]


@router.post("/actions/{action_id}/approve")
async def approve_action(
    action_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    action = await session.get(AgentAction, action_id)
    if not action:
        raise HTTPException(status_code=404, detail="action not found")
    action.approved_by = current_user.id
    await session.commit()
    return {"status": "approved"}


@router.post("/actions/{action_id}/refuse")
async def refuse_action(
    action_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    action = await session.get(AgentAction, action_id)
    if not action:
        raise HTTPException(status_code=404, detail="action not found")
    action.result = {"refused": True, "refused_by": current_user.id}
    await session.commit()
    return {"status": "refused"}
