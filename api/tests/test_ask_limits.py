"""/ask's limits, counted in Postgres so every copy of the API shares them (ADR 0006)."""

import asyncio
from datetime import UTC, date, datetime

import psycopg
from psycopg.rows import TupleRow
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from quiet_camps.api.ask_limits import COUNT, count_ask, day_start, hour_start, viewer_bucket
from quiet_camps.api.settings import Settings

WINDOW = datetime(2026, 11, 23, 9, tzinfo=UTC)


async def counts(settings: Settings, *windows: tuple[str, datetime]) -> list[int]:
    engine = create_async_engine(settings.database_url)
    try:
        found: list[int] = []
        for bucket, starts in windows:
            async with AsyncSession(engine) as session:
                found.append(await count_ask(session, bucket, starts))
        return found
    finally:
        await engine.dispose()


def test_counts_up_within_a_window(
    api_settings: Settings, conn: psycopg.Connection[TupleRow]
) -> None:
    found = asyncio.run(counts(api_settings, *[("site", WINDOW)] * 3))

    assert found == [1, 2, 3]


def test_each_bucket_and_window_counts_on_its_own(
    api_settings: Settings, conn: psycopg.Connection[TupleRow]
) -> None:
    later = datetime(2026, 11, 23, 10, tzinfo=UTC)
    found = asyncio.run(
        counts(api_settings, ("site", WINDOW), ("203.0.113.9", WINDOW), ("site", later))
    )

    assert found == [1, 1, 1]


async def race_at_299(settings: Settings) -> tuple[bool, int]:
    """One ask holds the row (counted, not yet committed) while a second arrives."""
    engine = create_async_engine(settings.database_url)
    try:
        async with AsyncSession(engine) as first, AsyncSession(engine) as second:
            assert (
                await first.execute(COUNT, {"bucket": "site", "starts": WINDOW})
            ).scalar() == 300
            waiting = asyncio.create_task(count_ask(second, "site", WINDOW))
            await asyncio.sleep(0.3)
            blocked = not waiting.done()  # Postgres makes it wait for the first's row lock
            await first.commit()
            return blocked, await waiting
    finally:
        await engine.dispose()


def test_two_asks_at_once_never_get_the_same_count(
    api_settings: Settings, conn: psycopg.Connection[TupleRow]
) -> None:
    conn.execute("INSERT INTO ask_count (bucket, starts, n) VALUES ('site', %s, 299)", (WINDOW,))
    conn.commit()

    blocked, second = asyncio.run(race_at_299(api_settings))

    assert blocked
    assert second == 301  # not 300: only one of the two is the 300th


def test_an_ipv4_viewer_is_their_address() -> None:
    assert viewer_bucket("203.0.113.9") == "203.0.113.9"


def test_ipv6_viewers_on_one_network_share_a_bucket() -> None:
    # A /64 is one home or phone network; its devices can pick any address inside it.
    assert viewer_bucket("2001:db8:1:2:aaaa::1") == "2001:db8:1:2::/64"
    assert viewer_bucket("2001:db8:1:2:bbbb:cccc:dddd:9") == "2001:db8:1:2::/64"
    assert viewer_bucket("2001:db8:1:3::1") != viewer_bucket("2001:db8:1:2::1")


def test_something_that_isnt_an_address_is_its_own_bucket() -> None:
    assert viewer_bucket("testclient") == "testclient"


def test_windows_start_on_queensland_days_and_hours() -> None:
    assert day_start(date(2026, 11, 23)) == datetime(2026, 11, 22, 14, tzinfo=UTC)  # midnight AEST
    assert hour_start(datetime(2026, 11, 23, 9, 41, 7, tzinfo=UTC)) == WINDOW
