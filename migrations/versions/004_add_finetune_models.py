"""Add fine-tuning tables: audio_uploads, datasets, dataset_tracks, finetune_jobs, lora_adapters.

Revision ID: 004
Revises: 003
Create Date: 2026-03-16

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- audio_uploads ---
    op.create_table(
        "audio_uploads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("storage_key", sa.String(1024), nullable=False),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=False),
        sa.Column("duration_seconds", sa.Float, nullable=False),
        sa.Column("format", sa.String(10), nullable=False),
        sa.Column("analysis", postgresql.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  onupdate=sa.func.now(), nullable=True),
    )

    # --- datasets ---
    op.create_table(
        "datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, server_default="", nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("num_tracks", sa.Integer, server_default="0", nullable=False),
        sa.Column("total_duration_seconds", sa.Float, server_default="0", nullable=False),
        sa.Column("storage_prefix", sa.String(1024), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  onupdate=sa.func.now(), nullable=True),
    )

    # --- dataset_tracks ---
    op.create_table(
        "dataset_tracks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("datasets.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("upload_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("audio_uploads.id"), nullable=False),
        sa.Column("lyrics", sa.Text, server_default="", nullable=False),
        sa.Column("caption", sa.Text, server_default="", nullable=False),
        sa.Column("bpm", sa.Integer, nullable=True),
        sa.Column("key_scale", sa.String(30), nullable=True),
        sa.Column("duration_seconds", sa.Float, server_default="0", nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )

    # --- finetune_jobs ---
    op.create_table(
        "finetune_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("datasets.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending",
                  nullable=False, index=True),
        sa.Column("config", postgresql.JSON, server_default="{}", nullable=False),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("progress", sa.Integer, server_default="0", nullable=False),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  onupdate=sa.func.now(), nullable=True),
    )

    # --- lora_adapters ---
    op.create_table(
        "lora_adapters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("finetune_job_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("finetune_jobs.id"), unique=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, server_default="", nullable=False),
        sa.Column("storage_key", sa.String(1024), nullable=False),
        sa.Column("adapter_size_bytes", sa.BigInteger, nullable=False),
        sa.Column("base_model", sa.String(100), nullable=False),
        sa.Column("training_method", sa.String(20), server_default="lokr",
                  nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  onupdate=sa.func.now(), nullable=True),
    )

    # Add lora_adapter_id to generation_jobs for inference with custom style
    op.add_column(
        "generation_jobs",
        sa.Column("lora_adapter_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("lora_adapters.id"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("generation_jobs", "lora_adapter_id")
    op.drop_table("lora_adapters")
    op.drop_table("finetune_jobs")
    op.drop_table("dataset_tracks")
    op.drop_table("datasets")
    op.drop_table("audio_uploads")
