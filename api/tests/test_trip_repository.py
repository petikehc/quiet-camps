"""Trips from camp_night, against a fresh database: where the gaps-and-islands rules show."""

import asyncio
from datetime import date, timedelta

import psycopg
from psycopg.rows import TupleRow
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from quiet_camps.api.trip_repository import TripRepository
from quiet_camps.api.trip_service import Arrivals, TripSource
from quiet_camps.db.campgrounds import assign_campgrounds
from quiet_camps.db.config import database_url
from quiet_camps.db.load import ensure_areas

type Conn = psycopg.Connection[TupleRow]

PARK = "Great Sandy National Park"
AREA = "Teewah Beach camping zone 1"


def stay(
    conn: Conn,
    arrive: date,
    nights: int,
    *,
    postcode: str | None = "4000",
    state: str = "QLD",
    booked_on: date = date(2024, 6, 1),
    sites: int = 1,
    reservation_id: str | None = None,
    source_file: str = "q1.csv",
) -> None:
    """A booking's rows, as the files have them: one per site per night."""
    area_id = ensure_areas(conn, [(PARK, AREA)])[(PARK, AREA)]
    for i in range(nights):
        for _ in range(sites):
            conn.execute(
                "INSERT INTO camp_night (area_id, night, booked_on, adults, children, infants,"
                " postcode, state, reservation_id, source_file)"
                " VALUES (%s, %s, %s, 2, 0, 0, %s, %s, %s, %s)",
                (
                    area_id,
                    arrive + timedelta(days=i),
                    booked_on,
                    postcode,
                    state,
                    reservation_id,
                    source_file,
                ),
            )


def read(conn: Conn, first: date = date(2025, 1, 1)) -> list[Arrivals]:
    assign_campgrounds(conn)
    conn.commit()  # the repository reads on its own connection

    async def fetch() -> list[Arrivals]:
        engine = create_async_engine(database_url())
        try:
            async with AsyncSession(engine) as session:
                source: TripSource = TripRepository(session)
                return await source.arrivals(first, date(2025, 12, 31))
        finally:
            await engine.dispose()

    return asyncio.run(fetch())


def arrivals(conn: Conn) -> list[tuple[date, str | None, int]]:
    return [(a.night, a.postcode, a.sites) for a in read(conn)]


def test_a_stay_arrives_once_on_its_first_night(conn: Conn) -> None:
    stay(conn, date(2025, 4, 18), nights=3)

    assert arrivals(conn) == [(date(2025, 4, 18), "4000", 1)]


def test_a_gap_starts_another_stay(conn: Conn) -> None:
    stay(conn, date(2025, 4, 18), nights=2)
    stay(conn, date(2025, 4, 25), nights=2)  # the same booking a week later

    assert [night for night, _, _ in arrivals(conn)] == [date(2025, 4, 18), date(2025, 4, 25)]


def test_back_to_back_bookings_are_two_stays(conn: Conn) -> None:
    stay(conn, date(2025, 4, 18), nights=2, booked_on=date(2025, 1, 5))
    stay(conn, date(2025, 4, 20), nights=2, booked_on=date(2025, 3, 9))  # booked on another day

    assert arrivals(conn) == [(date(2025, 4, 18), "4000", 1), (date(2025, 4, 20), "4000", 1)]


def test_a_gap_stays_a_gap_when_another_booking_fills_it(conn: Conn) -> None:
    # Numbered together, the three nights would look like one run, and the first booking
    # would arrive once instead of twice.
    stay(conn, date(2025, 4, 18), nights=1, booked_on=date(2025, 1, 5))
    stay(conn, date(2025, 4, 19), nights=1, booked_on=date(2025, 3, 9))
    stay(conn, date(2025, 4, 20), nights=1, booked_on=date(2025, 1, 5))

    assert [night for night, _, _ in arrivals(conn)] == [
        date(2025, 4, 18),
        date(2025, 4, 19),
        date(2025, 4, 20),
    ]


def test_reservation_ids_keep_same_day_bookings_apart(conn: Conn) -> None:
    stay(conn, date(2025, 4, 18), nights=2, reservation_id="A1")
    stay(conn, date(2025, 4, 20), nights=2, reservation_id="B2")

    assert len(arrivals(conn)) == 2


def test_sites_are_per_night_and_bookings_from_one_postcode_add_up(conn: Conn) -> None:
    stay(conn, date(2025, 4, 18), nights=3, sites=3)
    stay(conn, date(2025, 4, 18), nights=1, booked_on=date(2024, 12, 2))

    assert arrivals(conn) == [(date(2025, 4, 18), "4000", 4)]


def test_a_stay_in_two_overlapping_files_counts_once(conn: Conn) -> None:
    for source_file in ("q1.csv", "q2.csv"):
        stay(conn, date(2025, 3, 30), nights=3, sites=2, source_file=source_file)

    assert arrivals(conn) == [(date(2025, 3, 30), "4000", 2)]


def test_a_stay_from_last_year_does_not_arrive_on_new_years_day(conn: Conn) -> None:
    stay(conn, date(2024, 12, 30), nights=4)

    assert arrivals(conn) == []


def test_overseas_and_missing_postcodes_still_arrive_for_the_counts(conn: Conn) -> None:
    stay(conn, date(2025, 7, 1), nights=1, postcode=None, state="UNKNOWN")
    stay(conn, date(2025, 7, 1), nights=1, postcode="8001", state="OVERSEAS")
    stay(conn, date(2025, 7, 1), nights=1, postcode=None, state="QLD")

    found = {(a.postcode, a.overseas) for a in read(conn)}
    assert found == {(None, True), ("8001", True), (None, False)}
