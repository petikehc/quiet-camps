"""fallback kinds

Revision ID: 9a689c75ba2a
Revises: 146c1bb87e5a
Create Date: 2026-11-24 09:03:38.979070

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9a689c75ba2a"
down_revision: str | Sequence[str] | None = "146c1bb87e5a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# campground_typical gains rows for each night's fallback kind (ingest/day_kinds.py): the
# weekday across a fortnight, a holiday's nights together, Christmas to New Year together. A
# query uses a night's own kind when it has enough history and its fallback when not. The
# per-kind rows are as before, plus how many years are behind each (a pool of a fortnight
# has twice the nights of a week, not twice the years); {fallback}, {years} and {pooled} are
# the only differences between the two versions.
CAMPGROUND_TYPICAL = """
CREATE MATERIALIZED VIEW campground_typical AS
WITH nightly AS (
    SELECT a.campground_id, n.night, sum(n.sites) AS sites, sum(n.campers) AS campers
    FROM area_night n
    JOIN camping_area a ON a.id = n.area_id
    GROUP BY a.campground_id, n.night
), history AS (
    SELECT date '2011-01-01' AS first,
           (date_trunc('quarter', max(night)) - interval '1 day')::date AS last
    FROM area_night
), open_month AS (
    SELECT DISTINCT campground_id, date_trunc('month', night)::date AS month FROM nightly
), every_night AS (
    SELECT o.campground_id, d.night::date AS night,
           coalesce(n.sites, 0) AS sites, coalesce(n.campers, 0) AS campers
    FROM open_month o
    CROSS JOIN LATERAL generate_series(
        o.month, o.month + interval '1 month' - interval '1 day', interval '1 day'
    ) AS d(night)
    LEFT JOIN nightly n ON n.campground_id = o.campground_id AND n.night = d.night::date
    CROSS JOIN history h
    WHERE d.night::date BETWEEN h.first AND h.last
      AND d.night::date NOT BETWEEN date '2020-03-26' AND date '2020-05-31'
), peak AS (
    SELECT campground_id, percentile_cont(0.95) WITHIN GROUP (ORDER BY sites) AS sites
    FROM every_night
    GROUP BY campground_id
), kinded AS (
    SELECT e.*, k.kind, {fallback} AS fallback_kind
    FROM every_night e
    JOIN calendar_day k ON k.night = e.night
)
SELECT e.campground_id, e.kind, count(*)::int AS nights,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY e.sites) AS sites,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY e.campers) AS campers,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY e.sites) / greatest(p.sites, 1) AS busyness,
       p.sites AS peak{years}
FROM kinded e
JOIN peak p ON p.campground_id = e.campground_id
GROUP BY e.campground_id, e.kind, p.sites{pooled}
"""
POOLED = """
UNION ALL
SELECT e.campground_id, e.fallback_kind, count(*)::int,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY e.sites),
       percentile_cont(0.5) WITHIN GROUP (ORDER BY e.campers),
       percentile_cont(0.5) WITHIN GROUP (ORDER BY e.sites) / greatest(p.sites, 1),
       p.sites, count(DISTINCT extract(year FROM e.night))::int
FROM kinded e
JOIN peak p ON p.campground_id = e.campground_id
WHERE e.fallback_kind IS NOT NULL
GROUP BY e.campground_id, e.fallback_kind, p.sites"""
INDEX = "CREATE UNIQUE INDEX ix_campground_typical_kind ON campground_typical (kind, campground_id)"


YEARS = ",\n       count(DISTINCT extract(year FROM e.night))::int AS years"


def rebuild(fallback: str, years: str, pooled: str) -> None:
    op.execute("DROP MATERIALIZED VIEW campground_typical")  # its index goes with it
    op.execute(CAMPGROUND_TYPICAL.format(fallback=fallback, years=years, pooled=pooled))
    op.execute(INDEX)


def upgrade() -> None:
    """Upgrade schema."""
    # Filled by fill_calendar on the next refresh (qc refresh, or qc load).
    op.add_column("calendar_day", sa.Column("fallback_kind", sa.String(), nullable=True))
    rebuild("k.fallback_kind", YEARS, POOLED)


def downgrade() -> None:
    """Downgrade schema."""
    rebuild("NULL::text", "", "")  # no longer reads the column, so it can go
    op.drop_column("calendar_day", "fallback_kind")
