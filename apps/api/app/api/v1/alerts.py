"""Alert webhook configuration endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.core.db import get_db
from app.models.models import Alert, User
from app.schemas import AlertCreate, AlertRead

router = APIRouter()

_VALID_TYPES = {"whatsapp", "telegram", "slack", "email"}


@router.get("", response_model=list[AlertRead])
async def list_alerts(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[Alert]:
    """List the current user's configured alert webhooks."""
    result = await session.execute(
        select(Alert)
        .where(Alert.user_id == user.id)
        .order_by(Alert.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("", response_model=AlertRead, status_code=status.HTTP_201_CREATED)
async def create_alert(
    data: AlertCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Alert:
    """Create a new alert webhook configuration."""
    if data.type not in _VALID_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"invalid alert type '{data.type}', must be one of: {', '.join(sorted(_VALID_TYPES))}",
        )

    alert = Alert(
        user_id=user.id,
        type=data.type,
        target=data.target,
        events=data.events,
    )
    session.add(alert)
    await session.commit()
    await session.refresh(alert)
    return alert


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    alert_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Delete an alert configuration."""
    alert = await session.get(Alert, alert_id)
    if not alert or alert.user_id != user.id:
        raise HTTPException(status_code=404, detail="alert not found")
    await session.delete(alert)
    await session.commit()
