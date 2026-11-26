"""campground qpws_url

Revision ID: b67b307bfaae
Revises: da017f900d5c
Create Date: 2026-11-26 10:56:56.567878

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b67b307bfaae"
down_revision: str | Sequence[str] | None = "da017f900d5c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Filled by `qc qpws-pages`, and again by qc load and qc refresh once it has run.
    op.add_column("campground", sa.Column("qpws_url", sa.String(), nullable=True))
    op.add_column("campground", sa.Column("qpws_url_kind", sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("campground", "qpws_url_kind")
    op.drop_column("campground", "qpws_url")
