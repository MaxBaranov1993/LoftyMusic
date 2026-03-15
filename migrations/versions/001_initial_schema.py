"""Initial schema: users, generation_jobs, tracks.

Revision ID: 001
Revises:
Create Date: 2026-03-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("clerk_id", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # Job status enum — use raw SQL to avoid SQLAlchemy auto-creation conflicts
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE job_status AS ENUM ('pending', 'queued', 'running', 'completed', 'failed', 'cancelled');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Generation jobs table
    op.create_table(
        "generation_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id", UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("status", sa.String(20), nullable=False, default="pending", index=True),
        sa.Column("prompt", sa.Text, nullable=False),
        sa.Column("duration_seconds", sa.Float, nullable=False, default=10.0),
        sa.Column("model_name", sa.String(100), nullable=False, default="musicgen-small"),
        sa.Column("generation_params", JSONB, nullable=False, server_default="{}"),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # Tracks table
    op.create_table(
        "tracks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "job_id", UUID(as_uuid=True),
            sa.ForeignKey("generation_jobs.id", ondelete="CASCADE"),
            nullable=False, unique=True,
        ),
        sa.Column(
            "user_id", UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("storage_key", sa.String(1024), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=False),
        sa.Column("duration_seconds", sa.Float, nullable=False),
        sa.Column("sample_rate", sa.Integer, nullable=False, default=32000),
        sa.Column("format", sa.String(10), nullable=False, default="wav"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("tracks")
    op.drop_table("generation_jobs")
    op.drop_table("users")
    sa.Enum(name="job_status").drop(op.get_bind(), checkfirst=True)
