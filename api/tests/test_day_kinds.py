from datetime import date

import pytest

from quiet_camps.ingest.day_kinds import day_kinds


def kinds(first: date, last: date) -> dict[date, str]:
    return {d.night: d.kind for d in day_kinds(first, last)}


def kind(night: date) -> str:
    return kinds(night, night)[night]


def test_easter_nights_line_up_across_years() -> None:
    # Good Friday 2024 was 29 March, and 18 April in 2025.
    assert kinds(date(2024, 3, 28), date(2024, 3, 31)) == {
        date(2024, 3, 28): "easter -1",  # Thursday night, before the long weekend
        date(2024, 3, 29): "easter +0",
        date(2024, 3, 30): "easter +1",
        date(2024, 3, 31): "easter +2",
    }
    assert kind(date(2025, 4, 19)) == "easter +1"


def test_easter_monday_night_is_an_ordinary_night() -> None:
    assert kind(date(2024, 4, 1)) == "week 14 1"  # back to work on Tuesday


def test_a_monday_holiday_gives_friday_to_sunday_nights() -> None:
    # Labour Day, Monday 6 May 2024.
    assert kinds(date(2024, 5, 3), date(2024, 5, 6)) == {
        date(2024, 5, 3): "labour day -3",
        date(2024, 5, 4): "labour day -2",
        date(2024, 5, 5): "labour day -1",
        date(2024, 5, 6): "week 19 1",
    }


def test_a_renamed_holiday_keeps_its_key() -> None:
    # Queen's Birthday on 3 Oct 2022, King's Birthday on 7 Oct 2024.
    assert kind(date(2022, 10, 2)) == kind(date(2024, 10, 6)) == "sovereign's birthday -1"


def test_a_midweek_holiday_marks_only_its_eve() -> None:
    # ANZAC Day, Thursday 25 April 2024: the Wednesday night before.
    assert kind(date(2024, 4, 24)) == "anzac day -1"
    assert kind(date(2024, 4, 25)) == "week 17 4"


@pytest.mark.parametrize("night", [date(2024, 12, 24), date(2024, 12, 31), date(2025, 1, 2)])
def test_christmas_to_new_year_compares_by_date(night: date) -> None:
    assert kind(night) == f"christmas {night:%m-%d}"


def test_ordinary_nights_compare_by_iso_week_and_weekday() -> None:
    assert kind(date(2024, 3, 9)) == "week 10 6"  # a Saturday
    assert kind(date(2025, 3, 8)) == "week 10 6"


def test_week_53_sits_with_week_52() -> None:
    assert kind(date(2020, 12, 23)) == "week 52 3"  # 2020 has an ISO week 53 ...
    assert kind(date(2026, 12, 23)) == "week 52 3"  # ... 2026 also has one


def test_a_one_off_holiday_is_an_ordinary_night() -> None:
    # The National Day of Mourning, Thursday 22 September 2022, has no other year to match.
    assert kind(date(2022, 9, 21)) == "week 38 3"


def test_every_night_has_one_kind_and_holiday_nights_say_which_holiday() -> None:
    nights = list(day_kinds(date(2011, 1, 1), date(2026, 12, 31)))
    assert len(nights) == len({d.night for d in nights}) == 5844
    assert all(d.holiday == d.kind.rsplit(" ", 1)[0] for d in nights if d.holiday)
    assert all(d.kind.startswith("week ") for d in nights if d.holiday is None)


def test_each_holiday_night_happens_once_a_year() -> None:
    nights = list(day_kinds(date(2011, 1, 1), date(2026, 12, 31)))
    per_year = [(d.night.year, d.kind) for d in nights if d.holiday]
    assert len(per_year) == len(set(per_year))


def test_each_night_falls_back_to_something_broader() -> None:
    nights = {d.night: d for d in day_kinds(date(2026, 12, 20), date(2027, 1, 4))}

    assert nights[date(2026, 12, 23)].fallback == "fortnight 26 3"  # week 52, a Wednesday
    assert nights[date(2026, 12, 25)].fallback == "christmas"
    assert nights[date(2027, 1, 4)].fallback == "fortnight 01 1"  # week 1, a Monday
    assert next(d for d in day_kinds(date(2027, 3, 26), date(2027, 3, 26))).fallback == "easter"


def test_every_coming_night_has_history_behind_its_kind_or_its_fallback() -> None:
    """Nights from now to 2029 against 2011 to 2025: three past nights of its own kind, or
    three past years of its fallback. Without the fallbacks, 23 December 2026 had two."""
    past = list(day_kinds(date(2011, 1, 1), date(2025, 12, 31)))
    nights_of: dict[str, int] = {}
    years_of: dict[str, set[int]] = {}
    for d in past:
        nights_of[d.kind] = nights_of.get(d.kind, 0) + 1
        years_of.setdefault(d.fallback, set()).add(d.night.year)

    short = [
        (d.night, d.kind)
        for d in day_kinds(date(2026, 1, 1), date(2029, 12, 31))
        if nights_of.get(d.kind, 0) < 3 and len(years_of.get(d.fallback, set())) < 3
    ]
    assert short == []


def test_school_holiday_nights_are_marked() -> None:
    """Queensland's 2024 winter school holidays were Saturday 22 June to Sunday 7 July: their
    nights are the evenings before each day off, Friday 21 June to Saturday 6 July."""
    marked = {d.night: d.school_holiday for d in day_kinds(date(2024, 6, 20), date(2024, 7, 7))}

    assert marked[date(2024, 6, 20)] is False  # a school night
    assert marked[date(2024, 6, 21)] is True
    assert marked[date(2024, 7, 6)] is True
    assert marked[date(2024, 7, 7)] is False  # school on Monday


def test_a_public_holiday_in_the_school_holidays_is_both() -> None:
    """Good Friday 2025 (18 April) was in the autumn school holidays."""
    [good_friday] = day_kinds(date(2025, 4, 18), date(2025, 4, 18))

    assert (good_friday.holiday, good_friday.school_holiday) == ("easter", True)
