"""add trigger_type column to workflows

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-30 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "workflows",
        sa.Column("trigger_type", sa.String(20), nullable=False, server_default="cron"),
    )


def downgrade() -> None:
    op.drop_column("workflows", "trigger_type")
