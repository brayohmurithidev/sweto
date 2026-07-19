"""cascade gym photo foreign keys on owner and gym deletion"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260719_gym_photo_cascade"
down_revision: str | Sequence[str] | None = "20260719_gym_photo_phase1"
branch_labels = None
depends_on = None


def _replace(
    table: str, name: str, referred: str, columns: list[str], ondelete: str
) -> None:
    op.drop_constraint(name, table, type_="foreignkey")
    op.create_foreign_key(name, table, referred, columns, ["id"], ondelete=ondelete)


def upgrade() -> None:
    _replace(
        "gym_photo_uploads",
        "fk_gym_photo_uploads_owner_user_id_users",
        "users",
        ["owner_user_id"],
        "CASCADE",
    )
    _replace(
        "gym_photo_uploads",
        "fk_gym_photo_uploads_gym_id_gyms",
        "gyms",
        ["gym_id"],
        "CASCADE",
    )
    _replace(
        "gym_photos",
        "fk_gym_photos_gym_id_gyms",
        "gyms",
        ["gym_id"],
        "CASCADE",
    )


def downgrade() -> None:
    _replace(
        "gym_photo_uploads",
        "fk_gym_photo_uploads_owner_user_id_users",
        "users",
        ["owner_user_id"],
        "RESTRICT",
    )
    _replace(
        "gym_photo_uploads",
        "fk_gym_photo_uploads_gym_id_gyms",
        "gyms",
        ["gym_id"],
        "CASCADE",
    )
    _replace(
        "gym_photos",
        "fk_gym_photos_gym_id_gyms",
        "gyms",
        ["gym_id"],
        "CASCADE",
    )
