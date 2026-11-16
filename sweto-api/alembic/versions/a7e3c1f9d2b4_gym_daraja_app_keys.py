"""each gym's own Daraja app keys

Safaricom binds a Daraja app to the shortcode it goes live on, so every gym
needs its own consumer key and secret next to its passkey.

Revision ID: a7e3c1f9d2b4
Revises: d2a6c8f0b1e5
Create Date: 2026-11-16 11:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a7e3c1f9d2b4"
down_revision: str | Sequence[str] | None = "d2a6c8f0b1e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "gym_mpesa_accounts",
        sa.Column("consumer_key_encrypted", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "gym_mpesa_accounts",
        sa.Column("consumer_secret_encrypted", sa.String(length=512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("gym_mpesa_accounts", "consumer_secret_encrypted")
    op.drop_column("gym_mpesa_accounts", "consumer_key_encrypted")
