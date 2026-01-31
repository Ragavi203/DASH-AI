"""add ai_events table for llm metrics

Revision ID: 20260131_0002
Revises: 20260131_0001
Create Date: 2026-01-31
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260131_0002"
down_revision = "20260131_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if not insp.has_table("ai_events"):
        op.create_table(
            "ai_events",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("dataset_id", sa.String(length=36), sa.ForeignKey("datasets.id"), nullable=False),
            sa.Column("request_id", sa.String(length=64), nullable=False),
            sa.Column("source", sa.String(length=32), nullable=False),
            sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("model", sa.String(length=64), nullable=False, server_default=""),
            sa.Column("prompt_version", sa.String(length=32), nullable=False, server_default=""),
            sa.Column("usage_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("error", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        )
    # indexes (best-effort)
    try:
        op.create_index("ix_ai_events_dataset_id", "ai_events", ["dataset_id"])
    except Exception:
        pass
    try:
        op.create_index("ix_ai_events_request_id", "ai_events", ["request_id"])
    except Exception:
        pass


def downgrade() -> None:
    op.drop_index("ix_ai_events_request_id", table_name="ai_events")
    op.drop_index("ix_ai_events_dataset_id", table_name="ai_events")
    op.drop_table("ai_events")

