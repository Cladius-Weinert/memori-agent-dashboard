"""Telemetry endpoints — ship events to Elastic Observability."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.v1.auth import get_current_user
from app.models.models import User
from app.services.elastic_observability import is_configured, ping, ship_event, status

router = APIRouter()


class ClientTelemetryIn(BaseModel):
    event: str = Field(..., description="e.g. connection_error, agent_run, mcp_test")
    error: str | None = None
    endpoint: str | None = None
    device: str | None = None
    app_version: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


@router.get("/status")
async def telemetry_status() -> dict[str, Any]:
    base = status()
    if is_configured():
        base["ping"] = await ping()
    return base


@router.post("/client")
async def client_telemetry(data: ClientTelemetryIn) -> dict[str, Any]:
    """Ingest mobile client events (no auth — bootstrap may fail before token)."""
    payload = {
        "message": data.error or data.event,
        "labels.event": data.event,
        "url.full": data.endpoint or "",
        "device.model.name": data.device or "",
        "service.version": data.app_version or "",
        **{f"labels.{k}": v for k, v in data.extra.items()},
    }
    return await ship_event("client", payload)


@router.post("/event")
async def log_event(
    data: ClientTelemetryIn,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Authenticated telemetry from mobile or dashboard."""
    payload = {
        "message": data.error or data.event,
        "labels.event": data.event,
        "user.id": str(current_user.id),
        "user.email": current_user.email,
        "url.full": data.endpoint or "",
        "device.model.name": data.device or "",
        **data.extra,
    }
    return await ship_event("app", payload)
