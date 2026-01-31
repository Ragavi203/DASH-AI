"""init datasets + chat_messages

Revision ID: 20260131_0001
Revises: 
Create Date: 2026-01-31
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260131_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "datasets",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("share_id", sa.String(length=48), nullable=False),
        sa.Column("original_filename", sa.String(length=512), nullable=False),
        sa.Column("stored_path", sa.String(length=1024), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("analysis_json", sa.Text(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_datasets_id", "datasets", ["id"])
    op.create_index("ix_datasets_share_id", "datasets", ["share_id"], unique=True)

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("dataset_id", sa.String(length=36), sa.ForeignKey("datasets.id"), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("message_type", sa.String(length=16), nullable=False, server_default="text"),
        sa.Column("content_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_chat_messages_dataset_id", "chat_messages", ["dataset_id"])


def downgrade() -> None:
    op.drop_index("ix_chat_messages_dataset_id", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_index("ix_datasets_share_id", table_name="datasets")
    op.drop_index("ix_datasets_id", table_name="datasets")
    op.drop_table("datasets")

