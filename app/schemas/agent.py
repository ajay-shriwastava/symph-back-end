from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

MessageLogLevel = Optional[Literal["MINIMAL", "STANDARD", "VERBOSE"]]


class AgentCreate(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    model: str = Field(default="claude-sonnet-4-6", max_length=100)
    system_prompt: Optional[str] = None
    tools: List[str] = Field(default_factory=list)
    channels: List[str] = Field(default_factory=list)
    memory_enabled: bool = False
    message_log_level: MessageLogLevel = None


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    model: Optional[str] = Field(default=None, max_length=100)
    system_prompt: Optional[str] = None
    tools: Optional[List[str]] = None
    channels: Optional[List[str]] = None
    memory_enabled: Optional[bool] = None
    message_log_level: MessageLogLevel = None


class AgentOut(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    model: str
    system_prompt: Optional[str]
    tools: List[str]
    channels: List[str]
    memory_enabled: bool
    interaction_rules: Dict[str, Any] = Field(default_factory=dict)
    guardrails: Dict[str, Any] = Field(default_factory=dict)
    message_log_level: MessageLogLevel = None
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class AgentListOut(BaseModel):
    items: List[AgentOut]
    total: int
    skip: int
    limit: int


# ── Interaction rules schemas ─────────────────────────────────────────────────

class InteractionRules(BaseModel):
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_turns: int = Field(default=10, ge=1, le=100)
    response_style: str = Field(default="balanced")
    language: str = Field(default="en", max_length=10)


class AgentInteractionRulesUpdate(BaseModel):
    interaction_rules: InteractionRules


# ── Guardrails schemas ────────────────────────────────────────────────────────

class Guardrails(BaseModel):
    max_tokens_per_response: int = Field(default=2048, ge=1, le=32768)
    restricted_topics: List[str] = Field(default_factory=list)
    content_filter_level: str = Field(default="medium")
    rate_limit_per_minute: int = Field(default=60, ge=1, le=1000)


class AgentGuardrailsUpdate(BaseModel):
    guardrails: Guardrails
