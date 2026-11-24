"""Queensland state school holidays, from the reviewed list of the department's dates."""

from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from quiet_camps.api.campground_service import HolidaySpan, school_holiday_spans
from quiet_camps.ingest.school_holidays import SchoolHoliday, school_holidays


def test_the_list_reads_as_nights_from_the_evening_before_each_day_off() -> None:
    found = school_holidays()

    # Easter 2027's holidays: Friday 26 March to Sunday 11 April.
    autumn = next(h for h in found if h.first_night.year == 2027 and h.name == "autumn")
    assert (autumn.first_night, autumn.last_night) == (date(2027, 3, 25), date(2027, 4, 10))
    assert [h.first_night for h in found] == sorted(h.first_night for h in found)
    assert {h.name for h in found} == {"autumn", "winter", "spring", "summer"}


def test_comment_lines_are_skipped(tmp_path: Path) -> None:
    path = tmp_path / "holidays.csv"
    path.write_text("# a note\nfirst_day,last_day,name\n2027-06-26,2027-07-11,winter\n")

    assert school_holidays(path) == [
        SchoolHoliday(name="winter", first_night=date(2027, 6, 25), last_night=date(2027, 7, 10))
    ]


def test_summer_is_cut_at_the_years_ends() -> None:
    summer = SchoolHoliday(
        name="summer", first_night=date(2026, 12, 11), last_night=date(2027, 1, 25)
    )

    assert school_holiday_spans([summer], date(2026, 1, 1), date(2026, 12, 31)) == [
        HolidaySpan(name="summer", night=344, nights=21)
    ]
    assert school_holiday_spans([summer], date(2027, 1, 1), date(2027, 12, 31)) == [
        HolidaySpan(name="summer", night=0, nights=25)
    ]


def test_the_year_view_shades_school_holidays(client: TestClient) -> None:
    response = client.get("/campgrounds/quiet/year", params={"year": 2027})

    spans = response.json()["school_holidays"]
    assert {"name": "autumn", "night": 83, "nights": 17} in spans  # 25 Mar to 10 Apr


def test_a_year_without_published_dates_has_none(client: TestClient) -> None:
    assert (
        client.get("/campgrounds/quiet/year", params={"year": 2012}).json()["school_holidays"] == []
    )
