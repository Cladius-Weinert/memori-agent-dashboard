"""Agent run + SSE stream endpoints."""
from __future__ import annotations

import json
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.models import AgentAction, AgentJob
from app.schemas import AgentJobRead, AgentRunIn
from app.agent.planner import run_agent, run_agent_sync

router = APIRouter()


@router.post("/run", response_model=AgentJobRead, status_code=201)
async def run_agent_job(data: AgentRunIn, session: AsyncSession = Depends(get_db)) -> AgentJob:
    job = AgentJob(user_id=1, goal=data.goal, status="planning")  # user_id placeholder
    session.add(job)
    await session.commit()
    await session.refresh(job)

    # run in background (Celery worker would pick this up)
    import asyncio
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
async def stream_agent_job(job_id: int) -> StreamingResponse:
    """SSE stream of agent execution events."""
    async def event_generator() -> AsyncIterator[str]:
        # initial plan + step events would be pushed here in real implementation
        # For now, just send a single completion event
        yield f"data: {json.dumps({'type': 'done', 'status': 'done'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/actions/{action_id}/approve")
async def approve_action(action_id: int, session: AsyncSession = Depends(get_db)) -> dict[str, str]:
    action = await session.get(AgentAction, action_id)
    if not action:
        raise HTTPException(status_code=404, detail="action not found")
    action.approved_by = 1  # placeholder user_id
    # In a real system we'd now re-run the tool since it was approved
    await session.commit()
    return {"status": "approved"}


@router.post("/actions/{action_id}/refuse")
async def refuse_action(action_id: int, session: AsyncSession = Depends(get_db)) -> dict[str, str]:
    action = await session.get(AgentAction, action_id)
    if not action:
        raise HTTPException(status_code=404, detail="action not found")
    action.result = {"refused": True}
    await session.commit()
    return {"status": "refused"}
