"""campground_typical peak

Revision ID: 43df222bbf22
Revises: c11b50da0a99
Create Date: 2026-11-23 22:28:45.164073

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "43df222bbf22"
down_revision: str | Sequence[str] | None = "c11b50da0a99"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The view from 4c826dff5291, now also keeping each campground's busy night (its 95th
# percentile, `peak`): the search ranks equally quiet campgrounds by it, so a real campground
# at 0% comes before a bush camp whose busy night is one site. A view can't gain a column, so
# it's rebuilt; {peak} is the only difference between the two versions.
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
)
SELECT e.campground_id, k.kind, count(*)::int AS nights,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY e.sites) AS sites,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY e.campers) AS campers,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY e.sites) / greatest(p.sites, 1) AS busyness{peak}
FROM every_night e
JOIN calendar_day k ON k.night = e.night
JOIN peak p ON p.campground_id = e.campground_id
GROUP BY e.campground_id, k.kind, p.sites
"""
INDEX = "CREATE UNIQUE INDEX ix_campground_typical_kind ON campground_typical (kind, campground_id)"


def rebuild(peak: str) -> None:
    op.execute("DROP MATERIALIZED VIEW campground_typical")  # its index goes with it
    op.execute(CAMPGROUND_TYPICAL.format(peak=peak))
    op.execute(INDEX)


def upgrade() -> None:
    """Upgrade schema."""
    rebuild(",\n       p.sites AS peak")


def downgrade() -> None:
    """Downgrade schema."""
    rebuild("")
