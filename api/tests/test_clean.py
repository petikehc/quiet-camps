from datetime import date

import pytest

from quiet_camps.ingest.clean import State, clean_postcode, clean_state, parse_count, parse_date

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


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("07/04/0016", date(2016, 4, 7)),  # jan2016-mar2016, booked 7/03/2016
        ("23/8/0015", date(2015, 8, 23)),  # jul2015-sep2015, booked 9/09/2015
    ],
)
def test_a_year_typed_as_00yy_means_20yy(text: str, expected: date) -> None:
    assert parse_date(text) == expected


def test_a_00yy_date_that_does_not_exist_still_raises() -> None:
    with pytest.raises(ValueError):
        parse_date("31/02/0016")


def test_the_error_message_shows_the_bad_value() -> None:
    with pytest.raises(ValueError, match="not a date"):
        parse_date("not a date")


# --- Blanks and truthiness: "" vs "0" vs None ---


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3", 3),
        ("0", 0),  # zero people is a real answer, not a missing one
        (" 2 ", 2),
        ("", None),  # blank: not recorded
        ("  ", None),
    ],
)
def test_parse_count(text: str, expected: int | None) -> None:
    assert parse_count(text) == expected


def test_zero_is_not_none() -> None:
    # The truthiness trap: 0 and None are both falsy, so `x or None` or `if not x` mixes them up.
    assert parse_count("0") is not None


def test_parse_count_rejects_text_that_is_not_a_number() -> None:
    with pytest.raises(ValueError, match="many"):
        parse_count("many")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("4000", "4000"),
        ("4870 ", "4870"),  # trailing space
        ("810", "0810"),  # Northern Territory: the leading zero was lost in Excel
        ("0", None),  # placeholder for unknown or overseas
        ("", None),
        ("na", None),
        ("O.S", None),
        ("34", None),  # too short to be a postcode
        ("40001", None),  # overseas
        ("WS13DD", None),  # a UK postcode
        ("48⁷1", None),  # a real value with a superscript 7: str.isdigit() says True
    ],
)
def test_clean_postcode_keeps_only_australian_postcodes(text: str, expected: str | None) -> None:
    assert clean_postcode(text) == expected


# --- State: about 5,000 spellings down to 8 states and territories, OVERSEAS and UNKNOWN ---


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("QLD", State.QLD),
        ("Qld", State.QLD),
        ("QUEENSLAND", State.QLD),
        (" queensland ", State.QLD),
        ("Q", State.QLD),
        ("New  South Wales", State.NSW),  # double space
        ("nsw", State.NSW),
        ("Victoria", State.VIC),
        ("South Australia", State.SA),
        ("WA", State.WA),
        ("Tasmania", State.TAS),
        ("ACT", State.ACT),
        ("Australian Capital Territory", State.ACT),
        ("Northern Territory", State.NT),
    ],
)
def test_state_names_and_abbreviations(text: str, expected: State) -> None:
    assert clean_state(text, postcode=None) == expected


def test_a_named_state_beats_the_postcode() -> None:
    assert clean_state("NSW", postcode="4000") == State.NSW


@pytest.mark.parametrize(
    ("text", "postcode", "expected"),
    [
        ("", "4000", State.QLD),
        ("Unknown", "2000", State.NSW),
        ("Australia", "0810", State.NT),
        ("", "2600", State.ACT),  # Canberra sits inside the NSW 2xxx block
        ("", "2900", State.ACT),
        ("", "3000", State.VIC),
        ("", "5000", State.SA),
        ("", "6000", State.WA),
        ("", "7000", State.TAS),
        ("", None, State.UNKNOWN),
        ("unknown", None, State.UNKNOWN),
    ],
)
def test_no_state_falls_back_to_the_postcode(
    text: str, postcode: str | None, expected: State
) -> None:
    assert clean_state(text, postcode=postcode) == expected


@pytest.mark.parametrize(
    ("text", "postcode"),
    [
        ("Overseas", None),
        ("Germany", None),
        ("Bavaria", None),
        ("Zurich", "8001"),  # a Swiss postcode is 4 digits too: don't read it as Victoria
        ("Auckland", "1010"),
    ],
)
def test_other_places_are_overseas(text: str, postcode: str | None) -> None:
    assert clean_state(text, postcode=postcode) == State.OVERSEAS


def test_state_is_a_string_enum() -> None:
    assert State.QLD == "QLD"
    assert f"{State.NSW}" == "NSW"
