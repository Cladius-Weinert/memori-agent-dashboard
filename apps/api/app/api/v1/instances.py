"""Instance CRUD + test-connection endpoint."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.models import Instance
from app.schemas import InstanceCreate, InstanceRead, InstanceTestResult
from app.services.ssh_pool import ssh_pool

router = APIRouter()


@router.post("", response_model=InstanceRead, status_code=status.HTTP_201_CREATED)
async def create_instance(data: InstanceCreate, session: AsyncSession = Depends(get_db)) -> Instance:
    inst = Instance(**data.model_dump())
    session.add(inst)
    await session.commit()
    await session.refresh(inst)
    return inst


@router.get("", response_model=list[InstanceRead])
async def list_instances(session: AsyncSession = Depends(get_db)) -> list[Instance]:
    result = await session.execute(select(Instance))
    return list(result.scalars().all())


@router.get("/{instance_id}", response_model=InstanceRead)
async def get_instance(instance_id: int, session: AsyncSession = Depends(get_db)) -> Instance:
    inst = await session.get(Instance, instance_id)
    if not inst:
        raise HTTPException(status_code=404, detail="instance not found")
    return inst


@router.post("/{instance_id}/test-connection", response_model=InstanceTestResult)
async def test_connection(instance_id: int, session: AsyncSession = Depends(get_db)) -> InstanceTestResult:
    inst = await session.get(Instance, instance_id)
    if not inst:
        raise HTTPException(status_code=404, detail="instance not found")
    try:
        # just try to connect via ssh_pool; it will load the instance and connect
        conn = await ssh_pool.acquire(instance_id)
        await ssh_pool.release(instance_id)
        return InstanceTestResult(instance_id=instance_id, ok=True, detail="SSH connection successful")
    except Exception as exc:
        return InstanceTestResult(instance_id=instance_id, ok=False, detail=str(exc))


@router.post("/{instance_id}/run-command")
async def run_command_on_instance(instance_id: int, command: str, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Run a single command on this instance (convenience endpoint)."""
    inst = await session.get(Instance, instance_id)
    if not inst:
        raise HTTPException(status_code=404, detail="instance not found")
    result = await ssh_pool.run_command(instance_id, command)
    return result
