"""`qc profile`: what the raw files really look like, before writing parsers for them."""

import csv
import functools
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator
from datetime import date, datetime
from pathlib import Path
from typing import NamedTuple

from quiet_camps.ingest.clean import normalise
from quiet_camps.ingest.profile import detect_encoding, group_by_header, value_shapes

TOP_SHAPES = 4


class NightsCheck(NamedTuple):
    reservations: int
    rows: int
    one_row_per_night: int  # distinct, consecutive stay dates, one row each
    starts_in_this_file: int  # first stay date == start date (others began last quarter)
    unparsed_dates: int


@functools.cache  # the same few thousand date strings repeat millions of times
def parse_day(text: str) -> date | None:
    """'1/07/2019' or '1/07/2019 0:00' → date. None when it isn't that format."""
    try:
        return datetime.strptime(text.split(" ")[0], "%d/%m/%Y").date()
    except ValueError:
        return None


def read_rows(path: Path) -> Iterator[list[str]]:
    """Every data row. errors='replace' because 4 files mix DOS bytes into cp1252."""
    with path.open(encoding=detect_encoding(path), errors="replace", newline="") as f:
        reader = csv.reader(f)
        next(reader)
        yield from reader


def check_nights(
    rows: Iterable[list[str]], id_col: int, start_col: int, stay_col: int
) -> NightsCheck:
    stays: defaultdict[str, list[date]] = defaultdict(list)
    starts: dict[str, date | None] = {}
    total = unparsed = 0
    for row in rows:
        total += 1
        stay = parse_day(row[stay_col])
        if stay is None:
            unparsed += 1
            continue
        stays[row[id_col]].append(stay)
        starts.setdefault(row[id_col], parse_day(row[start_col]))

    per_night = starts_here = 0
    for reservation, days in stays.items():
        distinct = set(days)
        if len(distinct) == len(days) and (max(days) - min(days)).days + 1 == len(days):
            per_night += 1
        if starts[reservation] == min(days):
            starts_here += 1
    return NightsCheck(len(stays), total, per_night, starts_here, unparsed)


def percent(part: int, whole: int) -> str:
    return f"{part / whole:.1%}" if whole else "n/a"


def column_index(header: tuple[str, ...], *names: str) -> int | None:
    normalised = [normalise(column) for column in header]
    for name in names:
        if name in normalised:
            return normalised.index(name)
    return None


def report_group(number: int, header: tuple[str, ...], paths: list[Path]) -> Iterator[str]:
    encodings = Counter(detect_encoding(path) for path in paths)
    by_encoding = ", ".join(f"{encoding} x{n}" for encoding, n in encodings.items())
    yield f"\n## Group {number}: {len(paths)} files ({by_encoding})"
    yield (
        f"   files: {paths[0].name} … {paths[-1].name}"
        if len(paths) > 1
        else f"   file: {paths[0].name}"
    )
    yield f"   header: {', '.join(header)}"

    id_col = 0 if any(w in normalise(header[0]) for w in ("id", "number")) else None
    start_col = column_index(header, "start date", "arrival date")
    stay_col = column_index(header, "stay date")

    # One file in memory at a time (the largest is 64 MB); the counts are added up.
    shapes = [Counter[str]() for _ in header]
    widths = Counter[int]()
    checks: list[NightsCheck] = []
    total = repeats = 0
    for path in paths:
        rows = list(read_rows(path))
        total += len(rows)
        widths.update(len(row) for row in rows)
        for i, counter in enumerate(shapes):
            counter.update(value_shapes(row[i] if i < len(row) else "<missing>" for row in rows))
        if id_col is not None and start_col is not None and stay_col is not None:
            checks.append(check_nights(rows, id_col, start_col, stay_col))
        elif id_col is not None:
            repeats += sum(n - 1 for n in Counter(tuple(row) for row in rows).values() if n > 1)

    yield f"   rows: {total:,}   row widths: {dict(widths)} (header has {len(header)})"
    for column, counter in zip(header, shapes, strict=True):
        top = ", ".join(f"{shape!r} x{n:,}" for shape, n in counter.most_common(TOP_SHAPES))
        more = f"  (+{len(counter) - TOP_SHAPES} more)" if len(counter) > TOP_SHAPES else ""
        yield f"   {column:>32}: {top}{more}"

    if checks:
        c = NightsCheck(*(sum(values) for values in zip(*checks, strict=True)))
        yield (
            f"   per-night check: {c.reservations:,} reservations in {c.rows:,} rows; "
            f"one row per night {percent(c.one_row_per_night, c.reservations)}; "
            f"starts in this file {percent(c.starts_in_this_file, c.reservations)}; "
            f"unparsed stay dates {c.unparsed_dates:,}"
        )
    elif id_col is not None:
        yield f"   rows that exactly repeat an earlier row: {repeats:,} ({percent(repeats, total)})"


def profile(data_dir: Path) -> Iterator[str]:
    paths = sorted(data_dir.glob("*.csv"))
    groups = group_by_header(paths)
    yield f"# Profile of {len(paths)} files in {data_dir}: {len(groups)} header layouts"
    for number, (header, names) in enumerate(groups.items(), start=1):
        yield from report_group(number, header, [data_dir / name for name in names])
