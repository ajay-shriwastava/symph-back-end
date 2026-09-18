import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class McpAuditLogOut(BaseModel):
    id: uuid.UUID
    caller_id: str
    tool_name: str
    agent_id: uuid.UUID | None
    params_summary: dict[str, Any]
    result_summary: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class McpAuditLogPage(BaseModel):
    items: list[McpAuditLogOut]
    total: int
    skip: int
    limit: int


class McpToolInfo(BaseModel):
    name: str
    category: str
    description: str