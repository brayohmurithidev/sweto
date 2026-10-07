"""preserve audit records when users are deleted"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260719_user_delete_fks"
down_revision: str | Sequence[str] | None = "20260719_gym_photo_cascade"
branch_labels = None
depends_on = None


def _replace(
    table: str,
    constraint: str,
    referred: str,
    column: str,
    ondelete: str,
) -> None:
    op.drop_constraint(constraint, table, type_="foreignkey")
    op.create_foreign_key(
        constraint, table, referred, [column], ["id"], ondelete=ondelete
    )


def upgrade() -> None:
    op.alter_column(
        "gym_verification_documents",
        "uploaded_by_user_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )
    _replace(
        "gym_verification_documents",
        "fk_gym_verification_documents_uploaded_by_user_id_users",
        "users",
        "uploaded_by_user_id",
        "SET NULL",
    )
    op.alter_column(
        "gym_verification_reviews",
        "reviewed_by_user_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )
    _replace(
        "gym_verification_reviews",
        "fk_gym_verification_reviews_reviewed_by_user_id_users",
        "users",
        "reviewed_by_user_id",
        "SET NULL",
    )
    _replace(
        "storage_uploads",
        "fk_storage_uploads_owner_user_id_users",
        "users",
        "owner_user_id",
        "CASCADE",
    )


def downgrade() -> None:
    _replace(
        "storage_uploads",
        "fk_storage_uploads_owner_user_id_users",
        "users",
        "owner_user_id",
        "RESTRICT",
    )
    _replace(
        "gym_verification_reviews",
        "fk_gym_verification_reviews_reviewed_by_user_id_users",
        "users",
        "reviewed_by_user_id",
        "RESTRICT",
    )
    op.alter_column(
        "gym_verification_reviews",
        "reviewed_by_user_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
    _replace(
        "gym_verification_documents",
        "fk_gym_verification_documents_uploaded_by_user_id_users",
        "users",
        "uploaded_by_user_id",
        "RESTRICT",
    )
    op.alter_column(
        "gym_verification_documents",
        "uploaded_by_user_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
