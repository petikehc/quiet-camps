"""How many asks /ask lets through: per viewer per hour, and for the whole site per day.

Counted in Postgres (the ask_count table), not in memory: on Lambda several copies of the API
run at once, and each would otherwise keep its own count (ADR 0006). One statement adds the
ask and returns the new count. Two asks at once can't both see 299: the second waits for the
first's row lock, then counts on from 300.
"""

import ipaddress
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

QUEENSLAND = ZoneInfo("Australia/Brisbane")
SITE = "site"  # the bucket for every ask, for the daily cap

COUNT = text("""
INSERT INTO ask_count (bucket, starts, n) VALUES (:bucket, :starts, 1)
ON CONFLICT (bucket, starts) DO UPDATE SET n = ask_count.n + 1
RETURNING n
""")


async def count_ask(session: AsyncSession, bucket: str, starts: datetime) -> int:
    """Count one ask in `bucket`'s window starting at `starts`; the count including it.

    Committed straight away, so an ask counts even if reading it fails afterwards.
    """
    n = (await session.execute(COUNT, {"bucket": bucket, "starts": starts})).scalar_one()
    await session.commit()
    return n


def viewer_bucket(address: str) -> str:
    """Whose asks these are: an IPv4 address, or an IPv6 address's /64.

    A /64 is one home or phone network, and its devices can choose any of its addresses, so
    counting by full IPv6 address would give one person millions of hourly limits.
    """
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return address  # not an address (the test client's "testclient"): its own bucket
    if ip.version == 6:
        return str(ipaddress.ip_network(f"{ip}/64", strict=False))
    return str(ip)


def day_start(today: date) -> datetime:
    """Queensland's midnight starting `today`: the daily cap's window."""
    return datetime.combine(today, time(), QUEENSLAND)


def hour_start(now: datetime) -> datetime:
    """The start of `now`'s hour: a viewer's window."""
    return now.replace(minute=0, second=0, microsecond=0)
