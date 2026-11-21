"""camp_night area and night index

Revision ID: a3f6c705d066
Revises: d103ef8eab2d
Create Date: 2026-11-21 10:19:01.171641

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3f6c705d066"
down_revision: str | Sequence[str] | None = "d103ef8eab2d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index("ix_camp_night_area_id_night", "camp_night", ["area_id", "night"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_camp_night_area_id_night", table_name="camp_night")
