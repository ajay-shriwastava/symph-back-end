import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.log import Log
from app.schemas.log import LogCreate, LogListOut, LogOut

router = APIRouter(prefix="/api/v1/logs", tags=["logs"])


def _row_to_out(row: Log) -> LogOut:
    return LogOut(
        id=row.id,
        level=row.level,
        message=row.message,
        agent_id=row.agent_id,
        workflow_id=row.workflow_id,
        metadata=row.metadata_,
        created_at=row.created_at,
    )


@router.get("", response_model=LogListOut)
async def list_logs(
    agent_id: Optional[uuid.UUID] = None,
    workflow_id: Optional[uuid.UUID] = None,
    level: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    q = select(Log)
    count_q = select(func.count()).select_from(Log)
    if agent_id:
        q = q.where(Log.agent_id == agent_id)
        count_q = count_q.where(Log.agent_id == agent_id)
    if workflow_id:
        q = q.where(Log.workflow_id == workflow_id)
        count_q = count_q.where(Log.workflow_id == workflow_id)
    if level:
        q = q.where(Log.level == level)
        count_q = count_q.where(Log.level == level)
    total = (await db.execute(count_q)).scalar_one()
    rows = (
        await db.execute(q.order_by(Log.created_at.desc()).offset(skip).limit(limit))
    ).scalars().all()
    return LogListOut(items=[_row_to_out(r) for r in rows], total=total, skip=skip, limit=limit)


@router.post("", response_model=LogOut, status_code=status.HTTP_201_CREATED)
async def create_log(
    body: LogCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    log = Log(
        level=body.level,
        message=body.message,
        agent_id=body.agent_id,
        workflow_id=body.workflow_id,
        metadata_=body.metadata,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return _row_to_out(log)


@router.get("/{log_id}", response_model=LogOut)
async def get_log(
    log_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    log = (await db.execute(select(Log).where(Log.id == log_id))).scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return _row_to_out(log)