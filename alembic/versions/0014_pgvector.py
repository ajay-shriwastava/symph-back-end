"""add pgvector extension and knowledge_base table

Revision ID: 0014
Revises: 0013
Create Date: 2026-08-14 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.execute("""
        CREATE TABLE knowledge_base (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            title       TEXT NOT NULL,
            content     TEXT NOT NULL,
            embedding   VECTOR(512),
            metadata_   JSONB NOT NULL DEFAULT '{}',
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # IVFFlat index for approximate nearest-neighbour search (cosine)
    # lists=100 is a sensible default for up to ~1M rows
    op.execute("""
        CREATE INDEX IF NOT EXISTS knowledge_base_embedding_idx
        ON knowledge_base
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    """)


def downgrade() -> None:
    op.drop_table("knowledge_base")
    # Leave the vector extension in place — other tables may use it
