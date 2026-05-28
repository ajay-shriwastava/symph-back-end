import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import get_db
from app.dependencies import get_current_user
from app.models.agent import Agent
from app.models.memory import AgentMemory
from app.schemas.agent import AgentCreate, AgentListOut, AgentOut, AgentUpdate
from app.schemas.memory import MemoryCreate, MemoryListOut, MemoryOut

router = APIRouter(prefix="/api/v1", tags=["agents"])


# ── Agents ──────────────────────────────────────────────────────────────────

@router.get("/agents", response_model=AgentListOut)
async def list_agents(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    total = (await db.execute(select(func.count()).select_from(Agent))).scalar_one()
    rows = (await db.execute(select(Agent).offset(skip).limit(limit))).scalars().all()
    return AgentListOut(items=rows, total=total, skip=skip, limit=limit)


@router.post("/agents", response_model=AgentOut, status_code=status.HTTP_201_CREATED)
async def create_agent(
    body: AgentCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    agent = Agent(**body.model_dump())
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


@router.get("/agents/{agent_id}", response_model=AgentOut)
async def get_agent(
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    agent = (await db.execute(select(Agent).where(Agent.id == agent_id))).scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.put("/agents/{agent_id}", response_model=AgentOut)
async def update_agent(
    agent_id: uuid.UUID,
    body: AgentUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    agent = (await db.execute(select(Agent).where(Agent.id == agent_id))).scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(agent, field, value)
    await db.commit()
    await db.refresh(agent)
    return agent


@router.delete("/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    agent = (await db.execute(select(Agent).where(Agent.id == agent_id))).scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    await db.delete(agent)
    await db.commit()


# ── Agent Memory ─────────────────────────────────────────────────────────────

@router.get("/agents/{agent_id}/memory", response_model=MemoryListOut)
async def list_memory(
    agent_id: uuid.UUID,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    _assert_agent_exists(agent_id, db)
    total = (
        await db.execute(
            select(func.count()).select_from(AgentMemory).where(AgentMemory.agent_id == agent_id)
        )
    ).scalar_one()
    rows = (
        await db.execute(
            select(AgentMemory).where(AgentMemory.agent_id == agent_id).offset(skip).limit(limit)
        )
    ).scalars().all()
    return MemoryListOut(items=rows, total=total, skip=skip, limit=limit)


@router.post("/agents/{agent_id}/memory", response_model=MemoryOut)
async def upsert_memory(
    agent_id: uuid.UUID,
    body: MemoryCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    stmt = (
        pg_insert(AgentMemory)
        .values(
            id=uuid.uuid4(),
            agent_id=agent_id,
            key=body.key,
            value=body.value,
        )
        .on_conflict_do_update(
            constraint="uq_agent_memory_agent_key",
            set_={"value": body.value, "updated_at": func.now()},
        )
        .returning(AgentMemory)
    )
    result = (await db.execute(stmt)).scalar_one()
    await db.commit()
    return result


@router.get("/agents/{agent_id}/memory/{key}", response_model=MemoryOut)
async def get_memory_entry(
    agent_id: uuid.UUID,
    key: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    entry = (
        await db.execute(
            select(AgentMemory).where(
                AgentMemory.agent_id == agent_id, AgentMemory.key == key
            )
        )
    ).scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Memory entry not found")
    return entry


@router.delete("/agents/{agent_id}/memory/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory_entry(
    agent_id: uuid.UUID,
    key: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    entry = (
        await db.execute(
            select(AgentMemory).where(
                AgentMemory.agent_id == agent_id, AgentMemory.key == key
            )
        )
    ).scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Memory entry not found")
    await db.delete(entry)
    await db.commit()


async def _assert_agent_exists(agent_id: uuid.UUID, db: AsyncSession) -> None:
    agent = (await db.execute(select(Agent).where(Agent.id == agent_id))).scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")