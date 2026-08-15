import uuid
from datetime import datetime

from pydantic import BaseModel


class KnowledgeIngestPayload(BaseModel):
    title: str
    content: str
    metadata: dict = {}


class KnowledgeEntryOut(BaseModel):
    id: uuid.UUID
    title: str
    content: str
    metadata: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeSearchPayload(BaseModel):
    query: str
    top_k: int = 5


class KnowledgeSearchResult(BaseModel):
    id: uuid.UUID
    title: str
    content: str
    metadata: dict
    score: float
