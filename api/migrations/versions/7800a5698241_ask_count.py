"""ask_count

Revision ID: 7800a5698241
Revises: b67b307bfaae
Create Date: 2026-11-26 12:57:43.947192

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7800a5698241"
down_revision: str | Sequence[str] | None = "b67b307bfaae"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Written by POST /ask, the one table the API writes: each viewer's asks per hour and the
    # site's per day, counted where every copy of the API sees them.
    op.create_table(
        "ask_count",
        sa.Column("bucket", sa.String(), nullable=False),
        sa.Column("starts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("n", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("bucket", "starts", name=op.f("pk_ask_count")),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("ask_count")
