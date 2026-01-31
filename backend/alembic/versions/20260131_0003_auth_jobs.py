"""auth + dataset status + jobs

Revision ID: 20260131_0003
Revises: 20260131_0002
Create Date: 2026-01-31
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260131_0003"
down_revision = "20260131_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    if not insp.has_table("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("email", sa.String(length=320), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        )
    try:
        op.create_index("ix_users_email", "users", ["email"], unique=True)
    except Exception:
        pass

    if not insp.has_table("login_codes"):
        op.create_table(
            "login_codes",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("email", sa.String(length=320), nullable=False),
            sa.Column("code_hash", sa.String(length=64), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        )
    try:
        op.create_index("ix_login_codes_email", "login_codes", ["email"])
    except Exception:
        pass

    # datasets: add user_id/status/error (SQLite-safe via batch)
    cols = {c["name"] for c in insp.get_columns("datasets")}
    with op.batch_alter_table("datasets") as b:
        if "user_id" not in cols:
            # SQLite batch mode requires named constraints; keep this as a plain nullable int in migrations.
            b.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        if "status" not in cols:
            b.add_column(sa.Column("status", sa.String(length=16), nullable=False, server_default="ready"))
        if "error" not in cols:
            b.add_column(sa.Column("error", sa.Text(), nullable=False, server_default=""))
        try:
            b.create_index("ix_datasets_user_id", ["user_id"])
        except Exception:
            pass

    if not insp.has_table("dataset_jobs"):
        op.create_table(
            "dataset_jobs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("dataset_id", sa.String(length=36), sa.ForeignKey("datasets.id"), nullable=False),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="queued"),
            sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("error", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
    try:
        op.create_index("ix_dataset_jobs_dataset_id", "dataset_jobs", ["dataset_id"])
    except Exception:
        pass


def downgrade() -> None:
    op.drop_index("ix_dataset_jobs_dataset_id", table_name="dataset_jobs")
    op.drop_table("dataset_jobs")

    with op.batch_alter_table("datasets") as b:
        b.drop_index("ix_datasets_user_id")
        b.drop_column("error")
        b.drop_column("status")
        b.drop_column("user_id")

    op.drop_index("ix_login_codes_email", table_name="login_codes")
    op.drop_table("login_codes")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

