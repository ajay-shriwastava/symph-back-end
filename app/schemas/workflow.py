from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class WorkflowCreate(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    graph_definition: Dict[str, Any] = Field(default_factory=dict)


class WorkflowUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    graph_definition: Optional[Dict[str, Any]] = None


class WorkflowOut(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    graph_definition: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class WorkflowListOut(BaseModel):
    items: List[WorkflowOut]
    total: int
    skip: int
    limit: int