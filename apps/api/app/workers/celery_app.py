"""Celery worker app for background agent jobs."""
from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "memori-agent",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "app.workers.tasks.*": {"queue": "agent"},
    },
)


@celery_app.task(name="app.workers.tasks.run_agent_job")
def run_agent_job(job_id: int) -> dict[str, str]:
    """Celery task to run an agent job from start to finish."""
    import asyncio
    from app.agent.planner import run_agent_sync
    from app.core.db import SessionLocal
    from app.models.models import AgentJob

    async def _run() -> None:
        async with SessionLocal() as session:
            job = await session.get(AgentJob, job_id)
            if not job:
                return
            job.status = "running"
            await session.commit()
            result = await run_agent_sync(job.goal)
            job.status = result.get("final_status", "failed")
            await session.commit()

    asyncio.run(_run())
    return {"status": "completed", "job_id": str(job_id)}
