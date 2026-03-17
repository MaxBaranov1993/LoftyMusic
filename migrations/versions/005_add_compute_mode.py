"""Add compute_mode column to generation_jobs and finetune_jobs.

Revision ID: 005
Revises: 004
Create Date: 2026-03-17

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "generation_jobs",
        sa.Column("compute_mode", sa.String(10), nullable=False, server_default="gpu"),
    )
    op.add_column(
        "finetune_jobs",
        sa.Column("compute_mode", sa.String(10), nullable=False, server_default="gpu"),
    )


def downgrade() -> None:
    op.drop_column("finetune_jobs", "compute_mode")
    op.drop_column("generation_jobs", "compute_mode")
