"""Agent configuration sub-resources: interaction rules, guardrails."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.agent import Agent
from app.schemas.agent import (
    AgentGuardrailsUpdate,
    AgentInteractionRulesUpdate,
    AgentOut,
)

router = APIRouter(prefix="/api/v1", tags=["agent-config"])


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_agent_or_404(agent_id: uuid.UUID, db: AsyncSession) -> Agent:
    agent = (
        await db.execute(select(Agent).where(Agent.id == agent_id))
    ).scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


# ── Interaction Rules ─────────────────────────────────────────────────────────

@router.put("/agents/{agent_id}/interaction-rules", response_model=AgentOut)
async def update_interaction_rules(
    agent_id: uuid.UUID,
    body: AgentInteractionRulesUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    agent = await _get_agent_or_404(agent_id, db)
    agent.interaction_rules = body.interaction_rules.model_dump()
    await db.commit()
    await db.refresh(agent)
    return agent


# ── Guardrails ────────────────────────────────────────────────────────────────

@router.put("/agents/{agent_id}/guardrails", response_model=AgentOut)
async def update_guardrails(
    agent_id: uuid.UUID,
    body: AgentGuardrailsUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    agent = await _get_agent_or_404(agent_id, db)
    agent.guardrails = body.guardrails.model_dump()
    await db.commit()
    await db.refresh(agent)
    return agent
