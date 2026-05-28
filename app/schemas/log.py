from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel


class LogCreate(BaseModel):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"]
    message: str
    agent_id: Optional[UUID] = None
    workflow_id: Optional[UUID] = None
    metadata: Optional[Dict[str, Any]] = None


class LogOut(BaseModel):
    id: UUID
    level: str
    message: str
    agent_id: Optional[UUID]
    workflow_id: Optional[UUID]
    metadata: Optional[Dict[str, Any]]
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def model_validate(cls, obj, **kwargs):
        # Map metadata_ ORM attribute to metadata schema field
        if hasattr(obj, "metadata_"):
            obj.__dict__["metadata"] = obj.metadata_
        return super().model_validate(obj, **kwargs)


class LogListOut(BaseModel):
    items: List[LogOut]
    total: int
    skip: int
    limit: int