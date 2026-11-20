"""area_night

Revision ID: 394a734a6ffd
Revises: 29a03ad7c37e
Create Date: 2026-11-19 21:45:10.355130

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "394a734a6ffd"
down_revision: str | Sequence[str] | None = "29a03ad7c37e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# A booking-night is everything we know about it except the file it came from. Overlapping
# quarterly files repeat whole stays, with or without a reservation ID, so the same key finds
# both copies (GROUP BY puts NULLs together). Known cost: where two files describe a booking
# differently, both copies count (+319 of 4.6M sites with an ID, measured 19 Nov 2026).
BOOKING_NIGHT = (
    "area_id, night, reservation_id, booked_on, adults, children, infants, postcode, state"
)

AREA_NIGHT = f"""
CREATE MATERIALIZED VIEW area_night AS
WITH per_file AS (
    -- Identical rows inside one file are separate sites of one booking, so count them.
    SELECT {BOOKING_NIGHT},
           count(*) AS sites,
           count(*) * (coalesce(adults, 0) + coalesce(children, 0) + coalesce(infants, 0))
               AS campers
    FROM camp_night
    GROUP BY {BOOKING_NIGHT}, source_file
), per_booking AS (
    -- The same booking-night in two files is one booking: keep the larger copy, don't add.
    SELECT area_id, night, max(sites) AS sites, max(campers) AS campers
    FROM per_file
    GROUP BY {BOOKING_NIGHT}
)
SELECT area_id, night, sum(sites)::int AS sites, sum(campers)::int AS campers
FROM per_booking
GROUP BY area_id, night
"""


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(AREA_NIGHT)
    # Unique, so a lookup by area and night is one row and REFRESH ... CONCURRENTLY can work.
    op.create_index("ix_area_night_area_id", "area_night", ["area_id", "night"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP MATERIALIZED VIEW area_night")  # its index goes with it
