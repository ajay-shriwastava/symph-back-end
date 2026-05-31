from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class WorkflowCreate(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    status: str = Field(default="draft", max_length=20)
    graph_definition: Dict[str, Any] = Field(default_factory=dict)
    schedule: Optional[str] = Field(default=None, max_length=100)
    trigger_type: str = Field(default="cron", max_length=20)


class WorkflowUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = Field(default=None, max_length=20)
    graph_definition: Optional[Dict[str, Any]] = None
    schedule: Optional[str] = Field(default=None, max_length=100)
    trigger_type: Optional[str] = Field(default=None, max_length=20)


class WorkflowOut(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    status: str
    graph_definition: Dict[str, Any]
    schedule: Optional[str]
    trigger_type: str
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class WorkflowListOut(BaseModel):
    items: List[WorkflowOut]
    total: int
    skip: int
    limit: int