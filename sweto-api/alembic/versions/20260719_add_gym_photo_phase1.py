"""add dedicated gym photo persistence and upload intents"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260719_gym_photo_phase1"
down_revision: str | Sequence[str] | None = "ed00cf268c84"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gym_photos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("gym_id", sa.Uuid(), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("original_filename", sa.String(length=200), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("is_cover", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_gym_photos"),
        sa.UniqueConstraint("storage_key", name="uq_gym_photos_storage_key"),
    )
    op.create_index("ix_gym_photos_gym_id", "gym_photos", ["gym_id"])
    op.create_index(
        "ix_gym_photos_gym_display_order",
        "gym_photos",
        ["gym_id", "display_order"],
    )
    op.create_table(
        "gym_photo_uploads",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("gym_id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(length=50), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("original_filename", sa.String(length=200), nullable=False),
        sa.Column("declared_mime_type", sa.String(length=100), nullable=False),
        sa.Column("declared_size_bytes", sa.Integer(), nullable=False),
        sa.Column(
            "status", sa.String(length=50), nullable=False, server_default="pending"
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["gym_id"], ["gyms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_gym_photo_uploads"),
        sa.UniqueConstraint("storage_key", name="uq_gym_photo_uploads_storage_key"),
        sa.CheckConstraint(
            "declared_size_bytes > 0", name="ck_gym_photo_upload_size_positive"
        ),
    )
    op.create_index("ix_gym_photo_uploads_gym_id", "gym_photo_uploads", ["gym_id"])
    op.create_index(
        "ix_gym_photo_uploads_owner_user_id", "gym_photo_uploads", ["owner_user_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_gym_photo_uploads_owner_user_id", table_name="gym_photo_uploads")
    op.drop_index("ix_gym_photo_uploads_gym_id", table_name="gym_photo_uploads")
    op.drop_table("gym_photo_uploads")
    op.drop_index("ix_gym_photos_gym_display_order", table_name="gym_photos")
    op.drop_index("ix_gym_photos_gym_id", table_name="gym_photos")
    op.drop_table("gym_photos")
