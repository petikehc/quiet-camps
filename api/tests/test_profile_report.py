from datetime import date

from quiet_camps.ingest.profile_report import NightsCheck, check_nights, normalise, parse_day


def test_parse_day_accepts_short_days_and_a_midnight_time() -> None:
    assert parse_day("1/07/2019") == date(2019, 7, 1)
    assert parse_day("01/07/2019 0:00") == date(2019, 7, 1)
    assert parse_day("2019-07-01") is None
    assert parse_day("") is None


def test_column_names_compare_across_variants() -> None:
    assert normalise("Stay Date") == normalise("stay_date") == normalise(" STAY_DATE ")


def test_check_nights_counts_per_night_and_quarter_split_reservations() -> None:
    #        id    start         stay
    rows = [
        ["A", "1/07/2022", "1/07/2022"],  # A: 2 nights, starts in this file
        ["A", "1/07/2022", "2/07/2022"],
        ["B", "27/06/2022", "1/07/2022"],  # B: began last quarter
        ["C", "5/07/2022", "5/07/2022"],  # C: same night twice, so not one row per night
        ["C", "5/07/2022", "5/07/2022"],
        ["D", "9/07/2022", "not a date"],
    ]

    assert check_nights(rows, id_col=0, start_col=1, stay_col=2) == NightsCheck(
        reservations=3, rows=6, one_row_per_night=2, starts_in_this_file=2, unparsed_dates=1
    )
