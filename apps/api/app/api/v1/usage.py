"""Token usage and billing endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.core.db import get_db
from app.models.models import TokenUsage, User
from app.schemas import TokenUsageRead, UsageSummary

router = APIRouter()


@router.get("", response_model=UsageSummary)
async def get_usage_summary(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get current user's aggregate usage summary with per-model breakdown."""
    # Aggregate totals
    totals_q = await session.execute(
        select(
            func.coalesce(func.sum(TokenUsage.input_tokens), 0).label("total_input"),
            func.coalesce(func.sum(TokenUsage.output_tokens), 0).label("total_output"),
            func.coalesce(func.sum(TokenUsage.cost_usd), 0.0).label("total_cost"),
        ).where(TokenUsage.user_id == user.id)
    )
    totals = totals_q.one()

    # Per-model breakdown
    breakdown_q = await session.execute(
        select(
            TokenUsage.model,
            func.coalesce(func.sum(TokenUsage.input_tokens), 0).label("input"),
            func.coalesce(func.sum(TokenUsage.output_tokens), 0).label("output"),
            func.coalesce(func.sum(TokenUsage.cost_usd), 0.0).label("cost"),
        )
        .where(TokenUsage.user_id == user.id)
        .group_by(TokenUsage.model)
    )

    by_model: dict[str, dict[str, Any]] = {}
    for row in breakdown_q.all():
        by_model[row.model] = {
            "input_tokens": row.input,
            "output_tokens": row.output,
            "cost_usd": float(row.cost),
        }

    return {
        "total_input": totals.total_input,
        "total_output": totals.total_output,
        "total_cost": float(totals.total_cost),
        "by_model": by_model,
    }


@router.get("/history", response_model=list[TokenUsageRead])
async def get_usage_history(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[TokenUsage]:
    """Get paginated token usage history for the current user."""
    result = await session.execute(
        select(TokenUsage)
        .where(TokenUsage.user_id == user.id)
        .order_by(TokenUsage.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())
