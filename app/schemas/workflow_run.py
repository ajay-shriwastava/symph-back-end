from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel


class WorkflowRunCreate(BaseModel):
    input: Optional[Dict[str, Any]] = None


class WorkflowRunOut(BaseModel):
    id: UUID
    workflow_id: UUID
    status: str
    input: Optional[Dict[str, Any]]
    output: Optional[Dict[str, Any]]
    error: Optional[str]
    usage: Optional[Dict[str, Any]]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkflowRunListOut(BaseModel):
    items: List[WorkflowRunOut]
    total: int
    skip: int
    limit: int
