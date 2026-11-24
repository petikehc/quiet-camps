"""calendar_day school_holiday

Revision ID: da017f900d5c
Revises: 9a689c75ba2a
Create Date: 2026-11-24 13:19:44.864950

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "da017f900d5c"
down_revision: str | Sequence[str] | None = "9a689c75ba2a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Filled by fill_calendar on the next refresh (qc refresh, or qc load).
    op.add_column(
        "calendar_day",
        sa.Column("school_holiday", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("calendar_day", "school_holiday")
