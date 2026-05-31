"""Templates — list pre-built workflow templates and instantiate them."""

import copy
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.agent import Agent
from app.models.workflow import Workflow
from app.schemas.workflow import WorkflowOut
from app.templates import TEMPLATES, TEMPLATES_BY_ID

router = APIRouter(prefix="/api/v1/templates", tags=["templates"])


@router.get("")
async def list_templates(_: dict = Depends(get_current_user)):
    """Return all available workflow templates (metadata only, no instantiation)."""
    return [
        {
            "id":           t["id"],
            "name":         t["name"],
            "description":  t["description"],
            "schedule":     t.get("schedule"),
            "trigger_type": t.get("trigger_type", "cron"),
        }
        for t in TEMPLATES
    ]


@router.post("/{template_id}/instantiate", response_model=WorkflowOut, status_code=status.HTTP_201_CREATED)
async def instantiate_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """Create a new Workflow (and its agent, if configured) from a template."""
    tmpl = TEMPLATES_BY_ID.get(template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")

    # Deep-copy graph so we can patch agent_id without mutating the template
    graph_def = copy.deepcopy(tmpl["graph_definition"])

    # If the template includes an agent_config, create the agent in the DB
    agent_cfg = tmpl.get("agent_config")
    if agent_cfg:
        agent = Agent(
            id=uuid.uuid4(),
            name=agent_cfg["name"],
            description=agent_cfg.get("description"),
            model=agent_cfg.get("model", "claude-haiku-4-5-20251001"),
            system_prompt=agent_cfg.get("system_prompt"),
            tools=agent_cfg.get("tools", []),
            channels=agent_cfg.get("channels", []),
            memory_enabled=agent_cfg.get("memory_enabled", False),
        )
        db.add(agent)
        await db.flush()  # get agent.id without committing yet

        # Patch all agent nodes that have agent_id=None with the new agent's id
        for node in graph_def.get("nodes", []):
            if node.get("type") == "agent" and node.get("agent_id") is None:
                node["agent_id"] = str(agent.id)

    workflow = Workflow(
        name=tmpl["name"],
        description=tmpl["description"],
        status="draft",
        graph_definition=graph_def,
        schedule=tmpl.get("schedule"),
        trigger_type=tmpl.get("trigger_type", "cron"),
    )
    db.add(workflow)
    await db.commit()
    await db.refresh(workflow)

    # Register cron schedule if applicable
    if tmpl.get("trigger_type", "cron") == "cron" and tmpl.get("schedule"):
        try:
            from app.scheduler import register_workflow
            await register_workflow(str(workflow.id), tmpl["schedule"], tmpl["name"])
        except Exception:
            pass  # Scheduler may not be running in test environments

    return workflow
