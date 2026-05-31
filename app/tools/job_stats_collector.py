"""
job_stats_collector — Tool node + LangChain @tool

Queries the workflow_runs table and builds a job health summary covering
the last N hours (default 24).
"""

import logging
from datetime import datetime, timedelta, timezone

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LangChain @tool — used by real agent nodes
# ---------------------------------------------------------------------------

@tool
async def collect_job_stats(lookback_hours: int = 24) -> str:
    """Query workflow run statistics for the last N hours (default 24).
    Returns a plain-text summary covering: total runs, completed, failed, running,
    pending, success rate, per-workflow breakdown, and any failing workflows.
    Use this to gather data before writing an SRE health report."""
    from app.database import AsyncSessionLocal
    from app.models.workflow import Workflow
    from app.models.workflow_run import WorkflowRun
    from sqlalchemy import select
    from collections import defaultdict

    since = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

    async with AsyncSessionLocal() as db:
        runs = (await db.execute(
            select(WorkflowRun).where(WorkflowRun.created_at >= since)
        )).scalars().all()
        workflows = (await db.execute(select(Workflow))).scalars().all()
        wf_names = {str(w.id): w.name for w in workflows}

    total     = len(runs)
    completed = sum(1 for r in runs if r.status == "completed")
    failed    = sum(1 for r in runs if r.status == "failed")
    running   = sum(1 for r in runs if r.status == "running")
    pending   = sum(1 for r in runs if r.status == "pending")
    success_rate = round(completed / total * 100, 1) if total else 0.0

    wf_stats: dict = defaultdict(lambda: {"total": 0, "completed": 0, "failed": 0, "last_run": None})
    for r in runs:
        key = wf_names.get(str(r.workflow_id), str(r.workflow_id))
        wf_stats[key]["total"] += 1
        if r.status == "completed":
            wf_stats[key]["completed"] += 1
        elif r.status == "failed":
            wf_stats[key]["failed"] += 1
        ts = r.finished_at or r.started_at or r.created_at
        if ts and (wf_stats[key]["last_run"] is None or ts > wf_stats[key]["last_run"]):
            wf_stats[key]["last_run"] = ts

    failing = [name for name, s in wf_stats.items() if s["failed"] > 0]

    lines = [
        f"Job Health Summary — last {lookback_hours}h",
        f"  Total runs  : {total}",
        f"  Completed   : {completed}",
        f"  Failed      : {failed}",
        f"  Running     : {running}",
        f"  Pending     : {pending}",
        f"  Success rate: {success_rate}%",
        "",
        "Per-workflow breakdown:",
    ]
    for name, s in sorted(wf_stats.items()):
        last = s["last_run"].strftime("%Y-%m-%d %H:%M") if s["last_run"] else "never"
        lines.append(
            f"  {name}: {s['total']} runs | {s['completed']} ok | {s['failed']} failed | last: {last}"
        )
    if failing:
        lines += ["", f"ATTENTION — workflows with failures: {', '.join(failing)}"]

    logger.info("Job stats collected: %d total, %d failed", total, failed)
    return "\n".join(lines)


async def run(state: dict) -> dict:
    from app.database import AsyncSessionLocal
    from app.models.workflow import Workflow
    from app.models.workflow_run import WorkflowRun
    from sqlalchemy import select

    lookback_hours = int(state.get("lookback_hours", 24))
    since = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

    async with AsyncSessionLocal() as db:
        # All runs in the lookback window
        runs = (
            await db.execute(
                select(WorkflowRun).where(WorkflowRun.created_at >= since)
            )
        ).scalars().all()

        # All workflows for name lookup
        workflows = (await db.execute(select(Workflow))).scalars().all()
        wf_names = {str(w.id): w.name for w in workflows}

    # Aggregate totals
    total     = len(runs)
    completed = sum(1 for r in runs if r.status == "completed")
    failed    = sum(1 for r in runs if r.status == "failed")
    running   = sum(1 for r in runs if r.status == "running")
    pending   = sum(1 for r in runs if r.status == "pending")
    success_rate = round(completed / total * 100, 1) if total else 0.0

    # Per-workflow breakdown
    from collections import defaultdict
    wf_stats: dict = defaultdict(lambda: {"total": 0, "completed": 0, "failed": 0, "last_run": None})
    for r in runs:
        key = wf_names.get(str(r.workflow_id), str(r.workflow_id))
        wf_stats[key]["total"] += 1
        if r.status == "completed":
            wf_stats[key]["completed"] += 1
        elif r.status == "failed":
            wf_stats[key]["failed"] += 1
        ts = r.finished_at or r.started_at or r.created_at
        if ts and (wf_stats[key]["last_run"] is None or ts > wf_stats[key]["last_run"]):
            wf_stats[key]["last_run"] = ts

    # Failing workflows (any failures in window)
    failing = [name for name, s in wf_stats.items() if s["failed"] > 0]

    job_stats = {
        "lookback_hours": lookback_hours,
        "since": since.isoformat(),
        "total":        total,
        "completed":    completed,
        "failed":       failed,
        "running":      running,
        "pending":      pending,
        "success_rate": success_rate,
        "per_workflow": dict(wf_stats),
        "failing_workflows": failing,
    }

    # Build plain-text summary for the report agent
    lines = [
        f"Job Health Summary — last {lookback_hours}h",
        f"  Total runs  : {total}",
        f"  Completed   : {completed}",
        f"  Failed      : {failed}",
        f"  Running     : {running}",
        f"  Pending     : {pending}",
        f"  Success rate: {success_rate}%",
        "",
        "Per-workflow breakdown:",
    ]
    for name, s in sorted(wf_stats.items()):
        last = s["last_run"].strftime("%Y-%m-%d %H:%M") if s["last_run"] else "never"
        lines.append(
            f"  {name}: {s['total']} runs | "
            f"{s['completed']} ok | {s['failed']} failed | last: {last}"
        )

    if failing:
        lines += ["", f"ATTENTION — workflows with failures: {', '.join(failing)}"]

    summary = "\n".join(lines)
    logger.info("Job stats collected: %d total runs, %d failed", total, failed)

    return {
        **state,
        "job_stats": job_stats,
        "messages": list(state.get("messages", [])) + [summary],
    }
