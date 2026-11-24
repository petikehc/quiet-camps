"""Queensland state school holidays, from a reviewed list of the department's published dates
(qld_school_holidays.csv): for showing when families are camping and for how far ahead they
book, not (yet) for comparing nights, because only recent years are known."""

import csv
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

SCHOOL_HOLIDAYS_CSV = Path(__file__).with_name("qld_school_holidays.csv")


@dataclass(frozen=True, kw_only=True)
class SchoolHoliday:
    name: str  # autumn, winter, spring or summer
    first_night: date  # the evening before the first day off
    last_night: date  # the evening before the last day off


def school_holidays(path: Path = SCHOOL_HOLIDAYS_CSV) -> list[SchoolHoliday]:
    """In date order. Their nights are the evenings before each day off, as for public
    holidays (day_kinds.py): the Friday after the last day of term to the night before the
    first day back."""
    with path.open(newline="", encoding="utf-8") as f:
        rows = csv.DictReader(line for line in f if not line.startswith("#"))
        return sorted(
            (
                SchoolHoliday(
                    name=row["name"],
                    first_night=date.fromisoformat(row["first_day"]) - timedelta(days=1),
                    last_night=date.fromisoformat(row["last_day"]) - timedelta(days=1),
                )
                for row in rows
            ),
            key=lambda h: h.first_night,
        )
