"""From a raw permit CSV on disk to CampNights, whichever of the three families it is."""

import csv
from collections.abc import Callable, Iterable, Iterator, Sequence
from pathlib import Path
from typing import Literal

from quiet_camps.ingest.clean import normalise
from quiet_camps.ingest.parse import CampNight, parse_family_a, parse_family_b, parse_family_c
from quiet_camps.ingest.profile import detect_encoding, read_header

type Family = Literal["A", "B", "C"]
type Parser = Callable[[Iterable[dict[str, str]]], Iterator[CampNight]]

PARSERS: dict[Family, Parser] = {"A": parse_family_a, "B": parse_family_b, "C": parse_family_c}


def family_of(header: Sequence[str]) -> Family:
    """A: start date + days (2011 to Jun 2016). B: one row per night. C: arrival + departure."""
    columns = {normalise(column) for column in header}
    if "days" in columns:
        return "A"
    if "stay date" in columns:
        return "B"
    if "departure date" in columns:
        return "C"
    raise ValueError(f"not a known permit layout: {list(header)}")


def read_rows(path: Path) -> Iterator[dict[str, str]]:
    # errors="replace": 4 files mix MS-DOS bytes into Windows-1252 (only overseas state names).
    with path.open(encoding=detect_encoding(path), errors="replace", newline="") as f:
        yield from csv.DictReader(f)


def camp_nights(path: Path, rows: Iterable[dict[str, str]] | None = None) -> Iterator[CampNight]:
    """Every CampNight in one file. Pass `rows` to read them through something else first."""
    parse = PARSERS[family_of(read_header(path))]
    return parse(read_rows(path) if rows is None else rows)
