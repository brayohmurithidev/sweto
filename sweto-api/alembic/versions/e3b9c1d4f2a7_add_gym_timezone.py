"""add gyms.timezone for gym-local dates

Revision ID: e3b9c1d4f2a7
Revises: d7a2c5e9b3f1
Create Date: 2026-11-14 23:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e3b9c1d4f2a7"
down_revision: str | Sequence[str] | None = "d7a2c5e9b3f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "gyms",
        sa.Column(
            "timezone",
            sa.String(length=64),
            server_default="Africa/Nairobi",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("gyms", "timezone")
