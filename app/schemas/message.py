from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel


class MessageCreate(BaseModel):
    agent_id: UUID
    session_id: UUID
    role: Literal["user", "assistant", "system", "tool", "agent"]
    content: str


class MessageOut(BaseModel):
    id: UUID
    agent_id: UUID
    session_id: UUID
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageListOut(BaseModel):
    items: List[MessageOut]
    total: int
    skip: int
    limit: int