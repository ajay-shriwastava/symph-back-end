"""add usage column to workflow_runs

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-29 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "workflow_runs",
        sa.Column("usage", postgresql.JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("workflow_runs", "usage")
