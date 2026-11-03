"""Planner decision audit table.

Revision ID: 003
Revises: 002
Create Date: 2026-11-03
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "planner_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("trace_id", sa.String(32), nullable=False),
        sa.Column("session_id", sa.String(100), nullable=True),
        sa.Column("user_id", sa.String(100), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("planner_mode", sa.String(20), nullable=False),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("workflow", sa.String(50), nullable=True),
        sa.Column("intent", sa.String(50), nullable=True),
        sa.Column("entity_type", sa.String(50), nullable=True),
        sa.Column("entity_id", sa.String(100), nullable=True),
        sa.Column("entity_name", sa.String(120), nullable=True),
        sa.Column("metric", sa.String(100), nullable=True),
        sa.Column("dimension", sa.String(50), nullable=True),
        sa.Column("days", sa.Integer(), nullable=True),
        sa.Column("follow_up", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("clarification_message", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("raw_decision", postgresql.JSONB(), nullable=True),
        sa.Column("validation_result", sa.String(30), nullable=False),
        sa.Column("fallback_used", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("total_latency_ms", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_planner_decisions_trace_id", "planner_decisions", ["trace_id"])
    op.create_index("ix_planner_decisions_session_id", "planner_decisions", ["session_id"])
    op.create_index("ix_planner_decisions_user_id", "planner_decisions", ["user_id"])
    op.create_index("ix_planner_decisions_workflow", "planner_decisions", ["workflow"])
    op.create_index("ix_planner_decisions_fallback_used", "planner_decisions", ["fallback_used"])
    op.create_index("ix_planner_decisions_created_at", "planner_decisions", ["created_at"])


def downgrade() -> None:
    op.drop_table("planner_decisions")
