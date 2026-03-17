"""Add ACE-Step support: lyrics column on generation_jobs.

Revision ID: 003
Revises: 002
Create Date: 2026-03-16

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "generation_jobs",
        sa.Column("lyrics", sa.Text(), server_default="", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("generation_jobs", "lyrics")
