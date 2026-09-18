"""mcp_audit_log table

Revision ID: 0016
Revises: 0015
Create Date: 2026-09-18
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mcp_audit_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("caller_id", sa.String(255), nullable=False),
        sa.Column("tool_name", sa.String(100), nullable=False),
        sa.Column("agent_id", UUID(as_uuid=True), nullable=True),
        sa.Column("params_summary", JSONB, nullable=False, server_default="{}"),
        sa.Column("result_summary", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_mcp_audit_log_caller_id", "mcp_audit_log", ["caller_id"])
    op.create_index("ix_mcp_audit_log_created_at", "mcp_audit_log", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_mcp_audit_log_created_at", table_name="mcp_audit_log")
    op.drop_index("ix_mcp_audit_log_caller_id", table_name="mcp_audit_log")
    op.drop_table("mcp_audit_log")
