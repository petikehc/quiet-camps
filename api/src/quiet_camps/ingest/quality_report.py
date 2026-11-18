"""`qc quality`: what parsing kept, repeated and couldn't fill in, per file."""

from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import astuple
from pathlib import Path

from quiet_camps.ingest.files import camp_nights, family_of, read_rows
from quiet_camps.ingest.parse import CampNight
from quiet_camps.ingest.profile import read_header
from quiet_camps.ingest.quality import night_warnings


class Counted[T]:
    """Passes items through unchanged and counts them, so a generator can be measured."""

    def __init__(self, items: Iterable[T]) -> None:
        self.count = 0
        self._items = items

    def __iter__(self) -> Iterator[T]:
        for item in self._items:
            self.count += 1
            yield item


def reservation_night(night: CampNight) -> int | None:
    """The same booked site-night in two files has the same key. None without an ID.

    A hash, not the tuple itself, to keep 4.6M keys in memory (collisions: about 1 in a million).
    """
    if night.reservation_id is None:
        return None
    return hash((night.reservation_id, night.night, night.area, night.adults, night.children))


def quality(data_dir: Path) -> Iterator[str]:
    keys = Counter[int]()  # reservation-night → how many times it appears, across all files
    totals = Counter[str]()
    yield f"{'file':<42} fam {'rows':>9} {'nights':>10} {'repeats':>8}  warnings"

    for path in sorted(data_dir.glob("*.csv")):
        rows = Counted(read_rows(path))
        warnings: list[str] = []
        exact = Counter[tuple[object, ...]]()
        for night in camp_nights(path, rows):
            night_warnings(night, warnings)
            exact[astuple(night)] += 1
            if (key := reservation_night(night)) is not None:
                keys[key] += 1

        nights = exact.total()
        repeats = nights - len(exact)
        warned = Counter(warnings)
        listed = ", ".join(f"{w} {n:,}" for w, n in warned.most_common())
        family = family_of(read_header(path))
        yield f"{path.name:<42} {family:>3} {rows.count:>9,} {nights:>10,} {repeats:>8,}  {listed}"
        totals.update(
            {"files": 1, "rows": rows.count, "nights": nights, "repeated in a file": repeats}
        )
        totals.update(warned)

    totals["reservation-nights in more than one place"] = sum(n - 1 for n in keys.values() if n > 1)
    yield ""
    yield "totals:"
    for name, value in totals.items():
        yield f"  {name:<44} {value:>10,}"
