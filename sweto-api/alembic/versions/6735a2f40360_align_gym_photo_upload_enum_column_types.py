"""align gym photo upload enum column types

The phase-1 photo migration created gym_photo_uploads.purpose and .status as
VARCHAR(50), while the models declare non-native string enums. Alembic then
reported the difference on every autogenerate run. This aligns the database
with the models; stored values are unchanged.

Revision ID: 6735a2f40360
Revises: 20260719_user_delete_fks
Create Date: 2026-10-07 23:43:48.664981
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "6735a2f40360"
down_revision: str | Sequence[str] | None = "20260719_user_delete_fks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PURPOSE = sa.Enum("gym_photo", name="gym_photo_upload_purpose", native_enum=False)
_STATUS = sa.Enum(
    "pending",
    "completed",
    "failed",
    "expired",
    "cancelled",
    name="upload_status",
    native_enum=False,
)
_STATUS_DEFAULT = sa.text("'pending'::character varying")


def upgrade() -> None:
    op.alter_column(
        "gym_photo_uploads",
        "purpose",
        existing_type=sa.VARCHAR(length=50),
        type_=_PURPOSE,
        existing_nullable=False,
    )
    op.alter_column(
        "gym_photo_uploads",
        "status",
        existing_type=sa.VARCHAR(length=50),
        type_=_STATUS,
        existing_nullable=False,
        existing_server_default=_STATUS_DEFAULT,
    )


def downgrade() -> None:
    op.alter_column(
        "gym_photo_uploads",
        "status",
        existing_type=_STATUS,
        type_=sa.VARCHAR(length=50),
        existing_nullable=False,
        existing_server_default=_STATUS_DEFAULT,
    )
    op.alter_column(
        "gym_photo_uploads",
        "purpose",
        existing_type=_PURPOSE,
        type_=sa.VARCHAR(length=50),
        existing_nullable=False,
    )
