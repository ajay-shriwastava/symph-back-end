from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MemoryCreate(BaseModel):
    key: str = Field(..., max_length=255)
    value: str


class MemoryOut(BaseModel):
    id: UUID
    agent_id: UUID
    key: str
    value: str
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class MemoryListOut(BaseModel):
    items: List[MemoryOut]
    total: int
    skip: int
    limit: int