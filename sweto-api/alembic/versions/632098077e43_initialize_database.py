"""initialize database

Revision ID: 632098077e43
Revises:
Create Date: 2026-07-11 23:55:05.974114

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "632098077e43"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
