"""add gym 24 hour operating support

Revision ID: 0d66a60f95b3
Revises: 189758dbbc00
Create Date: 2026-07-17 12:13:20.103961
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0d66a60f95b3"
down_revision: str | Sequence[str] | None = "189758dbbc00"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add explicit support for 24-hour operating schedules."""

    op.add_column(
        "gym_operating_hours",
        sa.Column(
            "is_24_hours",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )

    op.drop_constraint(
        op.f("ck_gym_operating_hours_open_times_required_when_not_closed"),
        "gym_operating_hours",
        type_="check",
    )

    op.create_check_constraint(
        op.f("ck_gym_operating_hours_valid_schedule"),
        "gym_operating_hours",
        """
        (
            is_closed = true
            AND is_24_hours = false
            AND opens_at IS NULL
            AND closes_at IS NULL
        )
        OR
        (
            is_closed = false
            AND is_24_hours = true
            AND opens_at IS NULL
            AND closes_at IS NULL
        )
        OR
        (
            is_closed = false
            AND is_24_hours = false
            AND opens_at IS NOT NULL
            AND closes_at IS NOT NULL
            AND opens_at <> closes_at
        )
        """,
    )


def downgrade() -> None:
    """Remove explicit 24-hour operating support."""

    op.drop_constraint(
        op.f("ck_gym_operating_hours_valid_schedule"),
        "gym_operating_hours",
        type_="check",
    )

    op.create_check_constraint(
        op.f("ck_gym_operating_hours_open_times_required_when_not_closed"),
        "gym_operating_hours",
        ("is_closed = true OR (opens_at IS NOT NULL AND closes_at IS NOT NULL)"),
    )

    op.drop_column(
        "gym_operating_hours",
        "is_24_hours",
    )
