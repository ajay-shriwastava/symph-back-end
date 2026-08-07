"""add message_log_level to agents

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-04 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agents",
        sa.Column("message_log_level", sa.String(20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("agents", "message_log_level")
