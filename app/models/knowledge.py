import uuid
from datetime import datetime

from sqlalchemy import DateTime, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class KnowledgeEntry(Base):
    """
    A single text chunk in the knowledge base.

    The `embedding` column is declared as Text here so that SQLAlchemy/asyncpg
    does not attempt to decode the pgvector VECTOR type, which requires codec
    registration. All similarity queries are executed via raw text() SQL and
    never select the embedding column directly.
    """
    __tablename__ = "knowledge_base"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Stored as TEXT in the ORM; actual DB column is VECTOR(512) (set by migration).
    # Never read back through the ORM — queries use raw SQL instead.
    embedding: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
