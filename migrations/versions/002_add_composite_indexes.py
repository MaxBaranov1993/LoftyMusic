"""Add composite indexes for performance.

Revision ID: 002
Revises: 001
Create Date: 2026-03-15

"""
from typing import Sequence, Union

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Composite index for filtering jobs by user + status (used in has_active_job)
    op.create_index(
        "ix_generation_jobs_user_id_status",
        "generation_jobs",
        ["user_id", "status"],
    )

    # Composite index for listing jobs ordered by creation time (used in list_jobs)
    op.create_index(
        "ix_generation_jobs_user_id_created_at",
        "generation_jobs",
        ["user_id", "created_at"],
    )

    # Composite index for listing tracks by user ordered by creation time
    op.create_index(
        "ix_tracks_user_id_created_at",
        "tracks",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_tracks_user_id_created_at", table_name="tracks")
    op.drop_index("ix_generation_jobs_user_id_created_at", table_name="generation_jobs")
    op.drop_index("ix_generation_jobs_user_id_status", table_name="generation_jobs")
