"""add otp delivery channel

Records which channel (SMS or WhatsApp) carried each OTP challenge, so
delivery reports and a later fallback channel can be tied to the challenge.
Existing challenges were all sent by SMS.

Revision ID: a3c9d2e7f1b4
Revises: 6735a2f40360
Create Date: 2026-10-08 10:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a3c9d2e7f1b4"
down_revision: str | Sequence[str] | None = "6735a2f40360"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CHANNEL = sa.Enum("sms", "whatsapp", name="otp_delivery_channel", native_enum=False)


def upgrade() -> None:
    op.add_column(
        "otp_challenges",
        sa.Column(
            "delivery_channel",
            _CHANNEL,
            server_default="sms",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("otp_challenges", "delivery_channel")
