"""FastAPI application entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import auth, instances, terminal, commands, agent, models, system, memory, conversations, usage, alerts
from app.core.config import settings
from app.services.ssh_pool import ssh_pool


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # startup
    ssh_pool.start_gc()
    yield
    # shutdown
    await ssh_pool.stop()


app = FastAPI(
    title="Memori Agent & Dashboard API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(instances.router, prefix="/api/v1/instances", tags=["instances"])
app.include_router(terminal.router, prefix="/ws/terminal", tags=["terminal"])
app.include_router(commands.router, prefix="/api/v1/commands", tags=["commands"])
app.include_router(agent.router, prefix="/api/v1/agent", tags=["agent"])
app.include_router(models.router, prefix="/api/v1/models", tags=["models"])
app.include_router(system.router, prefix="/api/v1/system", tags=["system"])
app.include_router(memory.router, prefix="/api/v1/memory", tags=["memory"])
app.include_router(conversations.router, prefix="/api/v1/conversations", tags=["conversations"])
app.include_router(usage.router, prefix="/api/v1/usage", tags=["usage"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["alerts"])


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
