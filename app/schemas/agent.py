from datetime import datetime
from typing import Any, Dict, List, Optional
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
    skills: List[Any] = Field(default_factory=list)
    interaction_rules: Dict[str, Any] = Field(default_factory=dict)
    guardrails: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class AgentListOut(BaseModel):
    items: List[AgentOut]
    total: int
    skip: int
    limit: int


# ── Schedule schemas ──────────────────────────────────────────────────────────

class ScheduleCreate(BaseModel):
    label: str = Field(..., max_length=255)
    cron_expression: str = Field(..., max_length=100)
    enabled: bool = True


class ScheduleUpdate(BaseModel):
    label: Optional[str] = Field(default=None, max_length=255)
    cron_expression: Optional[str] = Field(default=None, max_length=100)
    enabled: Optional[bool] = None


class ScheduleOut(BaseModel):
    id: UUID
    agent_id: UUID
    label: str
    cron_expression: str
    enabled: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ScheduleListOut(BaseModel):
    items: List[ScheduleOut]
    total: int


# ── Skills schemas ────────────────────────────────────────────────────────────

class SkillItem(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    enabled: bool = True


class AgentSkillsUpdate(BaseModel):
    skills: List[SkillItem] = Field(default_factory=list)


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
