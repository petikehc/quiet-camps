"""Lead times group school-holiday nights on their own: families book them earlier than an
ordinary weeknight. A public holiday inside the school holidays stays that holiday."""

from datetime import date, timedelta

import psycopg
from fastapi.testclient import TestClient
from psycopg.rows import TupleRow

from quiet_camps.db.derived import refresh_derived
from quiet_camps.db.load import ensure_areas

Conn = psycopg.Connection[TupleRow]


def book(conn: Conn, night: date, weeks_ahead: int) -> None:
    key = ("Range NP", "Holiday Hollow camping area")
    area_id = ensure_areas(conn, [key])[key]
    conn.execute(
        "INSERT INTO camp_night (area_id, night, booked_on, adults, state, source_file)"
        " VALUES (%s, %s, %s, 2, 'QLD', 'q.csv')",
        (area_id, night, night - timedelta(weeks=weeks_ahead)),
    )


def test_school_holiday_nights_are_their_own_group(conn: Conn, client: TestClient) -> None:
    book(conn, date(2025, 4, 8), weeks_ahead=8)  # a Tuesday in the autumn school holidays
    book(conn, date(2025, 4, 18), weeks_ahead=12)  # Good Friday, in them too
    book(conn, date(2025, 5, 13), weeks_ahead=0)  # a Tuesday in term
    book(conn, date(2025, 8, 12), weeks_ahead=0)  # the latest quarter: not history yet
    list(refresh_derived(conn))
    conn.commit()
    [campground_id] = conn.execute("SELECT id FROM campground").fetchone() or [None]

    body = client.get(f"/campgrounds/{campground_id}/lead-time").json()

    assert [(g["group"], g["nights"]) for g in body["groups"]] == [
        ("easter", 1),
        ("school holidays", 1),
        ("weeknight", 1),
    ]
