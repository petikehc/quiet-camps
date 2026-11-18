from pathlib import Path

import pytest

from quiet_camps.ingest.files import camp_nights, family_of
from quiet_camps.ingest.quality_report import Counted, quality

HEADER_B = "Reservation Number,Type,Postcode,State,Booking Date,Start Date,Stay Date,Park,Facility,Adults,Children,Infants"  # noqa: E501
ROW_B = "576013,Camping,4000,QLD,1/02/2018,31/03/2018,{night},Conondale NP,Booloumba Creek 3,2,0,0"


@pytest.mark.parametrize(
    ("header", "family"),
    [
        (["POSTCODE", "STATE", "START_DATE", "DAYS", "ITEM_TYPE"], "A"),
        (["Camping Reservation Unique ID", "Stay Date", "Park"], "B"),
        (["stay_date", "park"], "B"),
        (["BookingID", "Arrival Date", "Departure Date"], "C"),
    ],
)
def test_family_of(header: list[str], family: str) -> None:
    assert family_of(header) == family


def test_an_unknown_layout_is_an_error() -> None:
    with pytest.raises(ValueError, match="not a known permit layout"):
        family_of(["Name", "Email"])


def write_b(path: Path, *nights: str) -> Path:
    lines = [HEADER_B, *(ROW_B.format(night=n) for n in nights)]
    path.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8-sig")
    return path


def test_camp_nights_reads_a_file_with_the_right_parser(tmp_path: Path) -> None:
    path = write_b(tmp_path / "b.csv", "31/03/2018", "1/04/2018")

    assert [n.night.isoformat() for n in camp_nights(path)] == ["2018-03-31", "2018-04-01"]


def test_counted_counts_what_passes_through() -> None:
    items = Counted(iter("abc"))

    assert list(items) == ["a", "b", "c"]
    assert items.count == 3


def test_quality_counts_a_night_that_appears_in_two_quarter_files(tmp_path: Path) -> None:
    # The real case from the profile: reservation 576013 is in both the Jan-Mar and Apr-Jun files.
    write_b(tmp_path / "q1.csv", "31/03/2018", "1/04/2018")
    write_b(tmp_path / "q2.csv", "1/04/2018", "2/04/2018", "2/04/2018")

    report = "\n".join(quality(tmp_path))

    lines = {line.split()[0]: line for line in report.splitlines() if line.strip()}
    assert lines["q2.csv"].split()[2:5] == ["3", "3", "1"]  # rows, nights, repeats in the file
    # 1 April is in both files, and 2 April twice in q2: 2 extra copies in all.
    [overlap] = [line for line in report.splitlines() if "in more than one place" in line]
    assert overlap.split()[-1] == "2"
