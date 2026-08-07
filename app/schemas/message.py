from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel

DestinationType = Optional[Literal["agent", "report", "display", "channel", "workflow"]]


class MessageCreate(BaseModel):
    agent_id: UUID
    session_id: UUID
    role: Literal["user", "assistant", "system", "tool", "agent"]
    content: str
    destination_type: DestinationType = None
    destination_ref: Optional[str] = None


class MessageOut(BaseModel):
    id: UUID
    agent_id: UUID
    session_id: UUID
    role: str
    content: str
    destination_type: Optional[str] = None
    destination_ref: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageListOut(BaseModel):
    items: List[MessageOut]
    total: int
    skip: int
    limit: int
