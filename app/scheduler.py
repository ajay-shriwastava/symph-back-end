"""
APScheduler integration.

On startup, reads all Workflow rows that have a `schedule` (cron string) and
registers a job for each one. New workflows can be registered at runtime via
register_workflow().
"""

import asyncio
import logging
import uuid

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


# ---------------------------------------------------------------------------
# Job function
# ---------------------------------------------------------------------------

async def _trigger_workflow(workflow_id_str: str) -> None:
    from app.database import AsyncSessionLocal
    from app.models.agent import Agent
    from app.models.workflow import Workflow
    from app.models.workflow_run import WorkflowRun
    from app.workflow_runner import run_workflow
    from sqlalchemy import select

    wf_uuid = uuid.UUID(workflow_id_str)

    # Create a pending run
    async with AsyncSessionLocal() as db:
        workflow = (
            await db.execute(select(Workflow).where(Workflow.id == wf_uuid))
        ).scalar_one_or_none()
        if not workflow:
            logger.warning("Scheduled workflow %s not found — skipping.", workflow_id_str)
            return

        run = WorkflowRun(workflow_id=wf_uuid, status="pending", input={})
        db.add(run)
        await db.commit()
        await db.refresh(run)
        run_id = str(run.id)
        graph_definition = workflow.graph_definition

    # Build agents map
    agent_ids = [
        n.get("agent_id")
        for n in graph_definition.get("nodes", [])
        if n.get("type") == "agent" and n.get("agent_id")
    ]
    agents_map: dict = {}
    if agent_ids:
        async with AsyncSessionLocal() as db:
            rows = (
                await db.execute(
                    select(Agent).where(
                        Agent.id.in_([uuid.UUID(str(a)) for a in agent_ids])
                    )
                )
            ).scalars().all()
            agents_map = {str(a.id): a for a in rows}

    # Execute in a fresh session
    async with AsyncSessionLocal() as bg_db:
        await run_workflow(
            run_id=run_id,
            workflow_id=workflow_id_str,
            graph_definition=graph_definition,
            agents_map=agents_map,
            input_data={},
            db=bg_db,
        )


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

async def start_scheduler() -> None:
    global _scheduler
    from app.database import AsyncSessionLocal
    from app.models.workflow import Workflow
    from sqlalchemy import select

    _scheduler = AsyncIOScheduler(timezone="UTC")

    async with AsyncSessionLocal() as db:
        workflows = (await db.execute(select(Workflow))).scalars().all()
        for wf in workflows:
            if wf.schedule:
                _add_job(str(wf.id), wf.schedule, wf.name)

    _scheduler.start()
    logger.info("Scheduler started with %d job(s).", len(_scheduler.get_jobs()))


async def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler stopped.")


async def register_workflow(workflow_id: str, schedule: str | None, name: str = "") -> None:
    """Register or update a scheduled job for a workflow at runtime."""
    if not _scheduler or not schedule:
        return
    _add_job(workflow_id, schedule, name)


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _add_job(workflow_id: str, cron: str, name: str) -> None:
    if not _scheduler:
        return
    try:
        trigger = CronTrigger.from_crontab(cron, timezone="UTC")
        _scheduler.add_job(
            _trigger_workflow,
            trigger,
            args=[workflow_id],
            id=f"wf_{workflow_id}",
            name=name or workflow_id,
            replace_existing=True,
            misfire_grace_time=30,
        )
        logger.info("Scheduled workflow '%s' (%s) with cron: %s", name, workflow_id, cron)
    except Exception as exc:
        logger.warning("Could not schedule workflow '%s': %s", name, exc)
