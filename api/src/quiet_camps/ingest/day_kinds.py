"""Which night of the year a date is, so nights compare across years like for like.

Ordinary nights compare by ISO week and weekday: Saturday of week 14 with every Saturday of
week 14. Holidays move, so their nights compare with the same night of the same holiday:
Easter Saturday 2024 (30 March) with Easter Saturday 2025 (19 April). 24 Dec to 2 Jan compares
by calendar date, because those dates don't move.

Some kinds come too seldom to say what's usual: the Wednesday of week 52 is inside 24 Dec to
2 Jan most years, so it's an ordinary night only every few years; a holiday on a Friday gives
nights other years don't have. Each night also has a broader kind to fall back on: an ordinary
night's weekday across its fortnight (weeks 51-52, Wednesdays), a holiday's nights all
together, Christmas to New Year together.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, timedelta

import holidays

# Recurring Queensland holidays, under one key across renames ("Queen's Birthday" became
# "King's Birthday" in 2023). One-offs such as the 2012 Jubilee are left out: no other year
# has one to compare with, so their nights stay ordinary.
HOLIDAY_KEYS = {
    "Australia Day": "australia day",
    "Good Friday": "easter",
    "Easter Saturday": "easter",
    "Easter Sunday": "easter",
    "Easter Monday": "easter",
    "ANZAC Day": "anzac day",
    "Labour Day": "labour day",
    "The Royal Queensland Show": "ekka",
    "Queen's Birthday": "sovereign's birthday",
    "King's Birthday": "sovereign's birthday",
}
CHRISTMAS_FROM = (12, 24)
CHRISTMAS_TO = (1, 2)


@dataclass(frozen=True)
class DayKind:
    night: date
    kind: str  # "week 14 6", "easter +1" or "christmas 12-31"
    holiday: str | None  # the holiday key, for showing the same holiday in other years
    fallback: str  # "fortnight 07 6", "easter" or "christmas": when kind is too seldom


def day_kinds(first: date, last: date) -> Iterator[DayKind]:
    """Every night from first to last, with its kind."""
    holiday_nights = _holiday_nights(first.year - 1, last.year + 1)
    night = first
    while night <= last:
        if _is_christmas(night):
            yield DayKind(night, f"christmas {night:%m-%d}", "christmas", "christmas")
        elif night in holiday_nights:
            key, offset = holiday_nights[night]
            yield DayKind(night, f"{key} {offset:+d}", key, key)
        else:
            _, week, weekday = night.isocalendar()
            # Week 53 comes every 5 or 6 years; it sits beside week 52, not week 1.
            week = min(week, 52)
            fortnight = (week + 1) // 2  # weeks 1-2 are fortnight 1, weeks 51-52 fortnight 26
            yield DayKind(
                night, f"week {week:02d} {weekday}", None, f"fortnight {fortnight:02d} {weekday}"
            )
        night += timedelta(days=1)


def _is_christmas(night: date) -> bool:
    month_day = (night.month, night.day)
    return month_day >= CHRISTMAS_FROM or month_day <= CHRISTMAS_TO


def _holiday_nights(first_year: int, last_year: int) -> dict[date, tuple[str, int]]:
    """{night: (holiday key, nights from the first day of the holiday)}.

    A holiday's nights are the evenings before each day of its run of days off: a Monday
    holiday gives Friday, Saturday and Sunday nights; Easter gives Thursday to Sunday.
    """
    public = holidays.country_holidays("AU", subdiv="QLD", years=range(first_year, last_year + 1))

    def day_off(day: date) -> bool:
        return day.weekday() >= 5 or day in public

    nights: dict[date, tuple[str, int]] = {}
    for day, names in sorted(public.items()):
        # Two holidays can share a day: 25 April 2011 was "ANZAC Day; Easter Monday".
        keys = [HOLIDAY_KEYS[name] for name in names.split("; ") if name in HOLIDAY_KEYS]
        if not keys or day - timedelta(days=1) in nights:
            continue  # not recurring, or already inside an earlier holiday's run (Easter)
        start = day
        while day_off(start - timedelta(days=1)):
            start -= timedelta(days=1)
        end = day
        while day_off(end + timedelta(days=1)):
            end += timedelta(days=1)
        night = start - timedelta(days=1)
        while night < end:
            nights.setdefault(night, (keys[0], (night - day).days))
            night += timedelta(days=1)
    return nights
