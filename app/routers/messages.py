import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.message import Message
from app.schemas.message import MessageCreate, MessageListOut, MessageOut

router = APIRouter(prefix="/api/v1/messages", tags=["messages"])


@router.get("", response_model=MessageListOut)
async def list_messages(
    session_id: Optional[uuid.UUID] = None,
    agent_id: Optional[uuid.UUID] = None,
    role: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    q = select(Message)
    count_q = select(func.count()).select_from(Message)
    if session_id:
        q = q.where(Message.session_id == session_id)
        count_q = count_q.where(Message.session_id == session_id)
    if agent_id:
        q = q.where(Message.agent_id == agent_id)
        count_q = count_q.where(Message.agent_id == agent_id)
    if role:
        q = q.where(Message.role == role)
        count_q = count_q.where(Message.role == role)
    total = (await db.execute(count_q)).scalar_one()
    rows = (
        await db.execute(q.order_by(Message.created_at).offset(skip).limit(limit))
    ).scalars().all()
    return MessageListOut(items=rows, total=total, skip=skip, limit=limit)


@router.post("", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
async def create_message(
    body: MessageCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    msg = Message(**body.model_dump())
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


@router.get("/{message_id}", response_model=MessageOut)
async def get_message(
    message_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    msg = (
        await db.execute(select(Message).where(Message.id == message_id))
    ).scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    return msg


@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    message_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    msg = (
        await db.execute(select(Message).where(Message.id == message_id))
    ).scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    await db.delete(msg)
    await db.commit()