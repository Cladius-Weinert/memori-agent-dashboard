"""Multi-instance command execution endpoint."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.models import Command, Instance
from app.schemas import CommandCreate, CommandRead
from app.services.ssh_pool import ssh_pool

router = APIRouter()


@router.post("", response_model=CommandRead, status_code=status.HTTP_201_CREATED)
async def execute_command(data: CommandCreate, session: AsyncSession = Depends(get_db)) -> Command:
    # verify all instances exist
    insts = await session.execute(select(Instance).where(Instance.id.in_(data.instance_ids)))
    if len(list(insts.scalars().all())) != len(data.instance_ids):
        raise HTTPException(status_code=404, detail="one or more instances not found")

    cmd = Command(instance_ids=data.instance_ids, command=data.command, status="running")
    session.add(cmd)
    await session.commit()
    await session.refresh(cmd)

    # execute in background via ssh_pool (fire-and-forget here; real impl would use Celery)
    import asyncio
    asyncio.create_task(_run_and_store(cmd.id, data.instance_ids, data.command))
    return cmd


async def _run_and_store(cmd_id: int, instance_ids: list[int], command: str) -> None:
    from app.core.db import SessionLocal
    from app.models.models import Command as Cmd
    outputs: dict[str, dict[str, Any]] = {}
    for iid in instance_ids:
        try:
            res = await ssh_pool.run_command(iid, command)
            outputs[str(iid)] = res
        except Exception as exc:
            outputs[str(iid)] = {"exit_code": -1, "stdout": "", "stderr": str(exc)}
    async with SessionLocal() as session:
        cmd = await session.get(Cmd, cmd_id)
        if cmd:
            cmd.outputs = outputs
            cmd.status = "done" if all(v.get("exit_code") == 0 for v in outputs.values()) else "failed"
            await session.commit()


@router.get("/{command_id}", response_model=CommandRead)
async def get_command(command_id: int, session: AsyncSession = Depends(get_db)) -> Command:
    cmd = await session.get(Command, command_id)
    if not cmd:
        raise HTTPException(status_code=404, detail="command not found")
    return cmd
