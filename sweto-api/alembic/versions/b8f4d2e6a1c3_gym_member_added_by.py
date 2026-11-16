"""who added each gym member

Revision ID: b8f4d2e6a1c3
Revises: a7e3c1f9d2b4
Create Date: 2026-11-16 20:40:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b8f4d2e6a1c3"
down_revision: str | Sequence[str] | None = "a7e3c1f9d2b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "gym_members",
        sa.Column("added_by_user_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_gym_members_added_by_user_id_users",
        "gym_members",
        "users",
        ["added_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_gym_members_added_by_user_id_users", "gym_members", type_="foreignkey"
    )
    op.drop_column("gym_members", "added_by_user_id")
