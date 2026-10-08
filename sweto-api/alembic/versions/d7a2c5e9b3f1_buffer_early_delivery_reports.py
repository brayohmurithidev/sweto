"""buffer delivery reports that arrive before their challenge is saved

Revision ID: d7a2c5e9b3f1
Revises: c4e8b1f2a9d6
Create Date: 2026-10-08 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d7a2c5e9b3f1"
down_revision: str | Sequence[str] | None = "c4e8b1f2a9d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "otp_unmatched_delivery_reports",
        sa.Column("provider_message_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("error_code", sa.String(length=32), nullable=True),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_otp_unmatched_delivery_reports")),
    )
    op.create_index(
        op.f("ix_otp_unmatched_delivery_reports_provider_message_id"),
        "otp_unmatched_delivery_reports",
        ["provider_message_id"],
    )
    op.create_index(
        op.f("ix_otp_unmatched_delivery_reports_received_at"),
        "otp_unmatched_delivery_reports",
        ["received_at"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_otp_unmatched_delivery_reports_received_at"),
        table_name="otp_unmatched_delivery_reports",
    )
    op.drop_index(
        op.f("ix_otp_unmatched_delivery_reports_provider_message_id"),
        table_name="otp_unmatched_delivery_reports",
    )
    op.drop_table("otp_unmatched_delivery_reports")
