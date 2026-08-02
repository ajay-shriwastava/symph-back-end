"""Agent configuration sub-resources: schedules, skills, interaction rules, guardrails."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.agent import Agent
from app.models.agent_schedule import AgentSchedule
from app.schemas.agent import (
    AgentGuardrailsUpdate,
    AgentInteractionRulesUpdate,
    AgentOut,
    ScheduleCreate,
    ScheduleListOut,
    ScheduleOut,
    ScheduleUpdate,
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


# ── Schedules ─────────────────────────────────────────────────────────────────

@router.get("/agents/{agent_id}/schedules", response_model=ScheduleListOut)
async def list_schedules(
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    await _get_agent_or_404(agent_id, db)
    total = (
        await db.execute(
            select(func.count()).select_from(AgentSchedule).where(
                AgentSchedule.agent_id == agent_id
            )
        )
    ).scalar_one()
    rows = (
        await db.execute(
            select(AgentSchedule)
            .where(AgentSchedule.agent_id == agent_id)
            .order_by(AgentSchedule.created_at)
        )
    ).scalars().all()
    return ScheduleListOut(items=rows, total=total)


@router.post(
    "/agents/{agent_id}/schedules",
    response_model=ScheduleOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_schedule(
    agent_id: uuid.UUID,
    body: ScheduleCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    await _get_agent_or_404(agent_id, db)
    schedule = AgentSchedule(
        id=uuid.uuid4(),
        agent_id=agent_id,
        **body.model_dump(),
    )
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    return schedule


@router.put("/agents/{agent_id}/schedules/{schedule_id}", response_model=ScheduleOut)
async def update_schedule(
    agent_id: uuid.UUID,
    schedule_id: uuid.UUID,
    body: ScheduleUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    await _get_agent_or_404(agent_id, db)
    schedule = (
        await db.execute(
            select(AgentSchedule).where(
                AgentSchedule.id == schedule_id,
                AgentSchedule.agent_id == agent_id,
            )
        )
    ).scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(schedule, field, value)
    await db.commit()
    await db.refresh(schedule)
    return schedule


@router.delete(
    "/agents/{agent_id}/schedules/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_schedule(
    agent_id: uuid.UUID,
    schedule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    await _get_agent_or_404(agent_id, db)
    schedule = (
        await db.execute(
            select(AgentSchedule).where(
                AgentSchedule.id == schedule_id,
                AgentSchedule.agent_id == agent_id,
            )
        )
    ).scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    await db.delete(schedule)
    await db.commit()


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
