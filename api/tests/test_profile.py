from collections import Counter
from pathlib import Path

from quiet_camps.ingest.profile import (
    detect_encoding,
    group_by_header,
    read_header,
    value_shapes,
)

HEADER = "Type,Postcode,State,Booking Date,Arrival Date"
ROW = "Camping,4000,QLD,01/06/2026,03/06/2026"
EXPECTED = ("Type", "Postcode", "State", "Booking Date", "Arrival Date")


def write(tmp_path: Path, name: str, content: bytes) -> Path:
    path = tmp_path / name
    path.write_bytes(content)
    return path


def test_utf8_with_and_without_bom_read_the_same(tmp_path: Path) -> None:
    text = f"{HEADER}\r\n{ROW}\r\n".encode()
    with_bom = write(tmp_path, "bom.csv", b"\xef\xbb\xbf" + text)
    without_bom = write(tmp_path, "plain.csv", text)

    assert detect_encoding(with_bom) == "utf-8-sig"
    assert detect_encoding(without_bom) == "utf-8-sig"
    # No "﻿" glued to "Type", and no "\r" left on "Arrival Date".
    assert read_header(with_bom) == EXPECTED
    assert read_header(without_bom) == EXPECTED


def test_windows_1252_file_is_detected_from_a_byte_after_the_header(tmp_path: Path) -> None:
    # A real case: a curly apostrophe saved by Windows as the single byte 0x92.
    row = "Camping,4000,QLD,01/06/2026,03/06/2026,Garry\x92s Anchorage".encode("latin-1")
    path = write(tmp_path, "cp1252.csv", HEADER.encode() + b"\r\n" + row + b"\r\n")

    assert detect_encoding(path) == "cp1252"
    assert read_header(path) == EXPECTED


def test_header_names_are_kept_exactly_as_written(tmp_path: Path) -> None:
    # Profiling reports the mess; cleaning it up is the parsers' job.
    path = write(tmp_path, "odd.csv", b"BookingID,Park Name ,camping_area\nx,y,z\n")

    assert read_header(path) == ("BookingID", "Park Name ", "camping_area")


def test_files_are_grouped_by_header_in_first_seen_order(tmp_path: Path) -> None:
    old = b"POSTCODE,STATE,START_DATE\r\n4000,QLD,1/07/2011\r\n"
    new = f"{HEADER}\r\n{ROW}\r\n".encode()
    paths = [
        write(tmp_path, "2026-q2.csv", new),
        write(tmp_path, "2011.csv", old),
        write(tmp_path, "2026-q3.csv", b"\xef\xbb\xbf" + new),  # same header, with a BOM
    ]

    groups = group_by_header(paths)

    assert groups == {
        EXPECTED: ["2026-q2.csv", "2026-q3.csv"],
        ("POSTCODE", "STATE", "START_DATE"): ["2011.csv"],
    }
    assert list(groups) == [EXPECTED, ("POSTCODE", "STATE", "START_DATE")]


def test_no_files_gives_no_groups() -> None:
    assert group_by_header([]) == {}


def test_value_shapes_replace_every_digit_with_9_and_count() -> None:
    values = ["1/07/2016", "01/06/2026", "12/12/2019", "", "N/A", "2016-07-01"]

    assert value_shapes(values) == Counter(
        {"99/99/9999": 2, "9/99/9999": 1, "": 1, "N/A": 1, "9999-99-99": 1}
    )


def test_value_shapes_accepts_any_iterable_such_as_a_generator() -> None:
    rows = [{"Postcode": "4000"}, {"Postcode": "486"}, {"Postcode": "4870"}]

    shapes = value_shapes(row["Postcode"] for row in rows)

    assert shapes.most_common(1) == [("9999", 2)]
