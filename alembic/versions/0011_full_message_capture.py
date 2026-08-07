"""add destination_type and destination_ref to messages

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-04 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("destination_type", sa.String(50), nullable=True))
    op.add_column("messages", sa.Column("destination_ref", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("messages", "destination_ref")
    op.drop_column("messages", "destination_type")
