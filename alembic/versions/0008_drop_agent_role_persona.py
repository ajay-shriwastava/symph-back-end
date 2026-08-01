"""drop role_persona column from agents

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-31 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("agents", "role_persona")


def downgrade() -> None:
    op.add_column("agents", sa.Column("role_persona", sa.Text, nullable=True))
