"""switch knowledge_base index from IVFFlat to HNSW

IVFFlat requires ~lists*3 rows before it returns results — unusable for small
knowledge bases.  HNSW works correctly at any scale with better recall.

Revision ID: 0015
Revises: 0014
Create Date: 2026-08-15 00:00:00.000000
"""

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS knowledge_base_embedding_idx")
    op.execute("""
        CREATE INDEX knowledge_base_embedding_idx
        ON knowledge_base
        USING hnsw (embedding vector_cosine_ops)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS knowledge_base_embedding_idx")
    op.execute("""
        CREATE INDEX knowledge_base_embedding_idx
        ON knowledge_base
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    """)
