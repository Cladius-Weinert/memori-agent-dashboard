"""FastAPI application entry point."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import auth, instances, terminal, commands, agent, models, system, memory, conversations, usage, alerts, catalog, workspace, mobile, telemetry
from app.api.v1 import settings as settings_api
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
app.include_router(catalog.router, prefix="/api/v1/catalog", tags=["catalog"])
app.include_router(workspace.router, prefix="/api/v1/workspace", tags=["workspace"])
app.include_router(mobile.router, prefix="/api/v1/mobile", tags=["mobile"])
app.include_router(telemetry.router, prefix="/api/v1/telemetry", tags=["telemetry"])
app.include_router(settings_api.router, prefix="/api/v1/settings", tags=["settings"])

# Elastic APM — optional, enabled when ELASTIC_APM_SERVER_URL is set
_apm_url = os.getenv("ELASTIC_APM_SERVER_URL", "")
if _apm_url:
    try:
        from elasticapm.contrib.starlette import ElasticAPM, make_apm_client

        _apm_client = make_apm_client({
            "SERVICE_NAME": os.getenv("ELASTIC_APM_SERVICE_NAME", "memori-agent-api"),
            "SERVER_URL": _apm_url,
            "SECRET_TOKEN": os.getenv("ELASTIC_APM_SECRET_TOKEN", ""),
            "ENVIRONMENT": os.getenv("ELASTIC_ENVIRONMENT", "production"),
            "TRANSACTIONS_IGNORE_PATTERNS": ["^GET /healthz"],
        })
        app.add_middleware(ElasticAPM, client=_apm_client)
    except ImportError:
        pass


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
