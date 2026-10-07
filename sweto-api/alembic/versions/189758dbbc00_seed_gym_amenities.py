"""seed gym amenities

Revision ID: 189758dbbc00
Revises: 1b8b54236712
Create Date: 2026-07-17

"""

from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa

from alembic import op

revision: str = "189758dbbc00"
down_revision: str | Sequence[str] | None = "1b8b54236712"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


AMENITY_IDS = [
    UUID("10000000-0000-4000-8000-000000000001"),
    UUID("10000000-0000-4000-8000-000000000002"),
    UUID("10000000-0000-4000-8000-000000000003"),
    UUID("10000000-0000-4000-8000-000000000004"),
    UUID("10000000-0000-4000-8000-000000000005"),
    UUID("10000000-0000-4000-8000-000000000006"),
    UUID("10000000-0000-4000-8000-000000000007"),
    UUID("10000000-0000-4000-8000-000000000008"),
    UUID("10000000-0000-4000-8000-000000000009"),
    UUID("10000000-0000-4000-8000-000000000010"),
    UUID("10000000-0000-4000-8000-000000000011"),
    UUID("10000000-0000-4000-8000-000000000012"),
    UUID("10000000-0000-4000-8000-000000000013"),
    UUID("10000000-0000-4000-8000-000000000014"),
    UUID("10000000-0000-4000-8000-000000000015"),
]


def upgrade() -> None:
    """Insert the initial gym amenity catalog."""

    amenities_table = sa.table(
        "amenities",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("slug", sa.String()),
        sa.column("description", sa.String()),
        sa.column("icon", sa.String()),
        sa.column("display_order", sa.Integer()),
        sa.column("is_active", sa.Boolean()),
    )

    op.bulk_insert(
        amenities_table,
        [
            {
                "id": AMENITY_IDS[0],
                "name": "Parking",
                "slug": "parking",
                "description": "On-site or designated parking is available.",
                "icon": "parking",
                "display_order": 10,
                "is_active": True,
            },
            {
                "id": AMENITY_IDS[1],
                "name": "Showers",
                "slug": "showers",
                "description": "Shower facilities are available.",
                "icon": "shower",
                "display_order": 20,
                "is_active": True,
            },
            {
                "id": AMENITY_IDS[2],
                "name": "Changing Rooms",
                "slug": "changing-rooms",
                "description": "Dedicated changing facilities are available.",
                "icon": "changing-room",
                "display_order": 30,
                "is_active": True,
            },
            {
                "id": AMENITY_IDS[3],
                "name": "Lockers",
                "slug": "lockers",
                "description": "Storage lockers are available.",
                "icon": "locker",
                "display_order": 40,
                "is_active": True,
            },
            {
                "id": AMENITY_IDS[4],
                "name": "Wi-Fi",
                "slug": "wifi",
                "description": "Wireless internet access is available.",
                "icon": "wifi",
                "display_order": 50,
                "is_active": True,
            },
            {
                "id": AMENITY_IDS[5],
                "name": "Swimming Pool",
                "slug": "swimming-pool",
                "description": "A swimming pool is available.",
                "icon": "pool",
                "display_order": 60,
                "is_active": True,
            },
            {
                "id": AMENITY_IDS[6],
                "name": "Sauna",
                "slug": "sauna",
                "description": "Sauna facilities are available.",
                "icon": "sauna",
                "display_order": 70,
                "is_active": True,
            },
            {
                "id": AMENITY_IDS[7],
                "name": "Steam Room",
                "slug": "steam-room",
                "description": "Steam-room facilities are available.",
                "icon": "steam",
                "display_order": 80,
                "is_active": True,
            },
            {
                "id": AMENITY_IDS[8],
                "name": "Personal Trainers",
                "slug": "personal-trainers",
                "description": "Personal training services are available.",
                "icon": "trainer",
                "display_order": 90,
                "is_active": True,
            },
            {
                "id": AMENITY_IDS[9],
                "name": "Group Classes",
                "slug": "group-classes",
                "description": "Instructor-led group classes are offered.",
                "icon": "group",
                "display_order": 100,
                "is_active": True,
            },
            {
                "id": AMENITY_IDS[10],
                "name": "Cardio Equipment",
                "slug": "cardio-equipment",
                "description": "Cardio machines and equipment are available.",
                "icon": "cardio",
                "display_order": 110,
                "is_active": True,
            },
            {
                "id": AMENITY_IDS[11],
                "name": "Strength Equipment",
                "slug": "strength-equipment",
                "description": "Strength and resistance equipment is available.",
                "icon": "dumbbell",
                "display_order": 120,
                "is_active": True,
            },
            {
                "id": AMENITY_IDS[12],
                "name": "Functional Training Area",
                "slug": "functional-training-area",
                "description": ("A dedicated functional training area is available."),
                "icon": "functional-training",
                "display_order": 130,
                "is_active": True,
            },
            {
                "id": AMENITY_IDS[13],
                "name": "Wheelchair Access",
                "slug": "wheelchair-access",
                "description": ("The facility supports wheelchair access."),
                "icon": "accessibility",
                "display_order": 140,
                "is_active": True,
            },
            {
                "id": AMENITY_IDS[14],
                "name": "Drinking Water",
                "slug": "drinking-water",
                "description": ("Drinking water or refill facilities are available."),
                "icon": "water",
                "display_order": 150,
                "is_active": True,
            },
        ],
    )


def downgrade() -> None:
    """Remove only the amenities inserted by this migration."""

    amenities_table = sa.table(
        "amenities",
        sa.column("id", sa.Uuid()),
    )

    op.execute(amenities_table.delete().where(amenities_table.c.id.in_(AMENITY_IDS)))
