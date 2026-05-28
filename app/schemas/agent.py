from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AgentCreate(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    role_persona: Optional[str] = None
    model: str = Field(default="claude-sonnet-4-6", max_length=100)
    system_prompt: Optional[str] = None
    tools: List[str] = Field(default_factory=list)
    channels: List[str] = Field(default_factory=list)
    memory_enabled: bool = False


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    role_persona: Optional[str] = None
    model: Optional[str] = Field(default=None, max_length=100)
    system_prompt: Optional[str] = None
    tools: Optional[List[str]] = None
    channels: Optional[List[str]] = None
    memory_enabled: Optional[bool] = None


class AgentOut(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    role_persona: Optional[str]
    model: str
    system_prompt: Optional[str]
    tools: List[str]
    channels: List[str]
    memory_enabled: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class AgentListOut(BaseModel):
    items: List[AgentOut]
    total: int
    skip: int
    limit: int