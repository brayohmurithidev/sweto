"""track otp delivery status and allow one pending code per number

- delivery_status, provider_message_id, delivery_status_updated_at and
  delivery_error_code record where a code is on its way to the user
  (WhatsApp delivery reports). They never change whether a code is usable.
- A partial unique index allows only one pending challenge per phone number
  and purpose, so racing requests can't leave two usable codes. Older
  duplicates are expired first, keeping the newest.

Revision ID: c4e8b1f2a9d6
Revises: a3c9d2e7f1b4
Create Date: 2026-10-08 11:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c4e8b1f2a9d6"
down_revision: str | Sequence[str] | None = "a3c9d2e7f1b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_STATUS = sa.Enum(
    "pending",
    "accepted",
    "sent",
    "delivered",
    "read",
    "failed",
    name="otp_delivery_status",
    native_enum=False,
)


def upgrade() -> None:
    op.add_column(
        "otp_challenges",
        sa.Column("provider_message_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "otp_challenges",
        sa.Column("delivery_status", _STATUS, server_default="pending", nullable=False),
    )
    op.add_column(
        "otp_challenges",
        sa.Column(
            "delivery_status_updated_at", sa.DateTime(timezone=True), nullable=True
        ),
    )
    op.add_column(
        "otp_challenges",
        sa.Column("delivery_error_code", sa.String(length=32), nullable=True),
    )
    op.create_unique_constraint(
        op.f("uq_otp_challenges_provider_message_id"),
        "otp_challenges",
        ["provider_message_id"],
    )
    op.execute(
        """
        UPDATE otp_challenges SET status = 'expired', updated_at = now()
        WHERE status = 'pending' AND id NOT IN (
            SELECT DISTINCT ON (phone_number, purpose) id
            FROM otp_challenges
            WHERE status = 'pending'
            ORDER BY phone_number, purpose, created_at DESC
        )
        """
    )
    op.create_index(
        "uq_otp_challenges_one_pending",
        "otp_challenges",
        ["phone_number", "purpose"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_otp_challenges_one_pending",
        table_name="otp_challenges",
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.drop_constraint(
        op.f("uq_otp_challenges_provider_message_id"),
        "otp_challenges",
        type_="unique",
    )
    op.drop_column("otp_challenges", "delivery_error_code")
    op.drop_column("otp_challenges", "delivery_status_updated_at")
    op.drop_column("otp_challenges", "delivery_status")
    op.drop_column("otp_challenges", "provider_message_id")
