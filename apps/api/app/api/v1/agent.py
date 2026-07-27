"""Agent run + SSE stream + chat endpoints."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import decode_token
from app.models.models import AgentAction, AgentJob, Conversation, ConversationMessage, User
from app.schemas import AgentJobRead, AgentRunIn, ConversationMessageCreate
from app.agent.planner import run_agent
from app.api.v1.auth import get_current_user

router = APIRouter()
_job_responses: dict[int, str] = {}


@router.post("/run", response_model=AgentJobRead, status_code=201)
async def run_agent_job(
    data: AgentRunIn,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AgentJob:
    conversation_id = data.conversation_id
    if conversation_id:
        conv = await session.get(Conversation, conversation_id)
        if not conv or conv.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="conversation not found")
        session.add(ConversationMessage(
            conversation_id=conversation_id,
            role="user",
            content=data.goal,
        ))
        conv.updated_at = datetime.now(timezone.utc)

    job = AgentJob(user_id=current_user.id, goal=data.goal, status="planning")
    session.add(job)
    await session.commit()
    await session.refresh(job)

    asyncio.create_task(_run_agent_background(job.id, data.goal, conversation_id))
    return job


async def _run_agent_background(job_id: int, goal: str, conversation_id: int | None = None) -> None:
    from app.core.db import SessionLocal
    final_response = ""
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
                result = ev.get("result", {})
                action = AgentAction(
                    job_id=job_id,
                    tool=ev.get("tool", ""),
                    params=ev.get("args", {}),
                    result=result,
                    requires_approval=bool(result.get("requires_approval")),
                )
                session.add(action)
            elif ev_type == "message":
                final_response = ev.get("content", "")
            elif ev_type == "done":
                job.status = ev.get("status", "done")
                if ev.get("response"):
                    final_response = ev.get("response", final_response)
            await session.commit()

        if conversation_id and final_response:
            _job_responses[job_id] = final_response
            session.add(ConversationMessage(
                conversation_id=conversation_id,
                role="agent",
                content=final_response,
                metadata_={"job_id": job_id},
            ))
            conv = await session.get(Conversation, conversation_id)
            if conv:
                conv.updated_at = datetime.now(timezone.utc)
            await session.commit()
        elif final_response:
            _job_responses[job_id] = final_response


@router.get("/jobs/{job_id}", response_model=AgentJobRead)
async def get_agent_job(job_id: int, session: AsyncSession = Depends(get_db)) -> AgentJob:
    job = await session.get(AgentJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="agent job not found")
    return job


@router.get("/jobs/{job_id}/stream")
async def stream_agent_job(
    job_id: int,
    token: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    if token and not decode_token(token):
        raise HTTPException(status_code=401, detail="invalid stream token")

    job = await session.get(AgentJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="agent job not found")

    async def event_generator() -> AsyncIterator[str]:
        from app.core.db import SessionLocal
        last_action_count = 0
        sent_plan = False
        sent_message = False
        while True:
            async with SessionLocal() as s:
                j = await s.get(AgentJob, job_id)
                if not j:
                    break

                actions = (await s.execute(
                    select(AgentAction).where(AgentAction.job_id == job_id).order_by(AgentAction.id)
                )).scalars().all()

                if j.plan and not sent_plan:
                    yield f"data: {json.dumps({'type': 'plan', 'plan': j.plan})}\n\n"
                    sent_plan = True

                for i, a in enumerate(actions):
                    if i >= last_action_count:
                        yield f"data: {json.dumps({'type': 'step', 'step': i, 'tool': a.tool, 'params': a.params, 'result': a.result or {}, 'requires_approval': a.requires_approval, 'action_id': a.id})}\n\n"

                last_action_count = len(actions)

                if j.status in ("done", "completed", "failed"):
                    if not sent_message and job_id in _job_responses:
                        yield f"data: {json.dumps({'type': 'message', 'content': _job_responses[job_id]})}\n\n"
                        sent_message = True
                    yield f"data: {json.dumps({'type': 'done', 'status': j.status})}\n\n"
                    break

            await asyncio.sleep(0.8)

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
    result = dict(action.result or {})
    if action.tool == "write_file" and result.get("requires_approval"):
        from app.services import workspace_fs
        path = result.get("path") or action.params.get("path", "")
        content = result.get("content") or action.params.get("content", "")
        try:
            workspace_fs.write_file(path, content)
            action.result = {**result, "written": True, "requires_approval": False}
        except Exception as exc:
            action.result = {**result, "error": str(exc)}
    elif action.tool == "git_commit" and result.get("requires_approval"):
        from app.services import workspace_git
        message = result.get("message") or action.params.get("message", "")
        exec_result = await workspace_git.git_commit(message)
        action.result = {**result, **exec_result, "requires_approval": False}
    elif action.tool == "run_command" and result.get("requires_approval"):
        from app.services.ssh_pool import ssh_pool
        instance_id = action.params.get("instance_id") or result.get("instance_id")
        command = action.params.get("command") or result.get("command", "")
        if instance_id and command:
            exec_result = await ssh_pool.run_command(int(instance_id), command)
            action.result = {"allowed": True, "instance_id": instance_id, **exec_result, "requires_approval": False}
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
