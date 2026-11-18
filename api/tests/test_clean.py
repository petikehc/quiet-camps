from datetime import date

import pytest

from quiet_camps.ingest.clean import parse_date

# Every date format the profile found, with the file it came from.


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1/07/2016", date(2016, 7, 1)),  # most files: short day, 4-digit year
        ("01/07/2016", date(2016, 7, 1)),
        ("1/7/2023", date(2023, 7, 1)),  # short month too (2016-2024 files)
        ("1/07/2019 0:00", date(2019, 7, 1)),  # 2019 files: midnight time on the end
        ("01/07/15", date(2015, 7, 1)),  # Oct 2015 to Mar 2016: 2-digit year
        ("14-Apr-16", date(2016, 4, 14)),  # Apr to Jun 2016: day-month name-year
        ("1-Jun-16", date(2016, 6, 1)),
        ("43831", date(2020, 1, 1)),  # Jan to Mar 2020: Excel serial number
        ("44012", date(2020, 6, 30)),
    ],
)
def test_parses_every_format_in_the_data(text: str, expected: date) -> None:
    assert parse_date(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "",
        "not a date",
        "31/02/2020",  # no 31st of February
        "2020-01-01",  # ISO: never appears in the data, so it shouldn't quietly pass
        "4000",  # a postcode in the wrong column, not Excel's 15 Dec 1910
        "999999",  # an Excel serial far in the future
    ],
)
def test_anything_else_raises_value_error(text: str) -> None:
    with pytest.raises(ValueError):
        parse_date(text)


def test_the_error_message_shows_the_bad_value() -> None:
    with pytest.raises(ValueError, match="not a date"):
        parse_date("not a date")
