import re
from datetime import date, datetime, timedelta
from enum import StrEnum

# Each format only matches its own shape ("%d/%m/%y" rejects "1/07/2016" and "%d/%m/%Y"
# rejects "01/07/15"), so the order doesn't matter. "%d/%m/%Y" does accept "07/04/0016" as
# the year 16: a typo in a few 2015-16 rows, which parse_date moves to 2016.
DATE_FORMATS = ("%d/%m/%Y", "%d/%m/%y", "%d-%b-%y")
EXCEL_EPOCH = date(1899, 12, 30)
# Only serials between 2000-01-01 and 2049-12-31 count as dates, so "4000" isn't 15 Dec 1910.
EXCEL_SERIALS = range(
    (date(2000, 1, 1) - EXCEL_EPOCH).days,
    (date(2050, 1, 1) - EXCEL_EPOCH).days,
)


def normalise(name: str) -> str:
    """Compare column names across variants: 'Stay Date', 'stay_date', 'STAY_DATE '."""
    return name.strip().lower().replace("_", " ")


def parse_date(text: str) -> date:
    """Any date format found in the permit files → date. Raises ValueError for anything else.

    '1/07/2016', '01/07/15', '14-Apr-16', '1/07/2019 0:00', and Excel serials such as '43831'.
    """
    value = text.split(" ")[0]

    if value.isdigit():
        serial = int(value)
        if serial in EXCEL_SERIALS:
            return EXCEL_EPOCH + timedelta(days=serial)
        raise ValueError(f"number out of the Excel date range: {text!r}")

    for date_format in DATE_FORMATS:
        try:
            parsed = datetime.strptime(value, date_format).date()
        except ValueError:
            continue

        if parsed.year < 100:
            return parsed.replace(year=parsed.year + 2000)
        return parsed

    raise ValueError(f"unrecognised date: {text!r}")


def parse_count(text: str) -> int | None:
    """A party size. Blank means 'not recorded' (None); '0' means nobody (0)."""
    value = text.strip()
    if value == "":
        return None
    return int(value)


def clean_postcode(text: str) -> str | None:
    """An Australian postcode as 4 digits, or None for blanks, placeholders and overseas codes."""
    value = text.strip()
    # Not str.isdigit(): that also accepts superscripts, and the data has a '48⁷1'.
    if not re.fullmatch(r"[0-9]{3,4}", value):
        return None
    if int(value) == 0:  # "0" is the export's placeholder for unknown or overseas
        return None
    return value.zfill(4)  # NT postcodes such as "810" lost their leading zero in Excel


class State(StrEnum):
    QLD = "QLD"
    NSW = "NSW"
    VIC = "VIC"
    SA = "SA"
    WA = "WA"
    TAS = "TAS"
    ACT = "ACT"
    NT = "NT"
    OVERSEAS = "OVERSEAS"
    UNKNOWN = "UNKNOWN"


# Spellings after collapsing spaces and casefolding. Together these cover 98% of rows.
STATE_NAMES: dict[State, tuple[str, ...]] = {
    State.QLD: ("qld", "queensland", "q"),
    State.NSW: ("nsw", "new south wales"),
    State.VIC: ("vic", "victoria"),
    State.SA: ("sa", "south australia"),
    State.WA: ("wa", "western australia"),
    State.TAS: ("tas", "tasmania"),
    State.ACT: ("act", "australian capital territory"),
    State.NT: ("nt", "northern territory"),
    State.OVERSEAS: ("overseas",),
}
# The same table turned around for lookups: {"qld": State.QLD, "queensland": State.QLD, ...}
NAME_TO_STATE: dict[str, State] = {
    value: state_short for state_short, values in STATE_NAMES.items() for value in values
}

# A state field that tells us nothing, so the postcode decides.
NO_STATE_GIVEN = ("", "unknown", "australia")

# Checked in order: the ACT ranges sit inside the NSW 2xxx block, so they come first.
POSTCODE_RANGES: tuple[tuple[int, int, State], ...] = (
    (200, 299, State.ACT),
    (2600, 2618, State.ACT),
    (2900, 2920, State.ACT),
    (800, 999, State.NT),
    (1000, 2999, State.NSW),
    (3000, 3999, State.VIC),
    (8000, 8999, State.VIC),
    (4000, 4999, State.QLD),
    (9000, 9999, State.QLD),
    (5000, 5999, State.SA),
    (6000, 6999, State.WA),
    (7000, 7999, State.TAS),
)


def state_from_postcode(postcode: str | None) -> State:
    if postcode is None:
        return State.UNKNOWN
    number = int(postcode)
    for low, high, state in POSTCODE_RANGES:
        if low <= number <= high:
            return state
    return State.UNKNOWN


def clean_state(text: str, postcode: str | None) -> State:
    """A named state wins; no state at all falls back to the (cleaned) postcode.

    Any other text is a place outside Australia. A postcode alone can't tell, because Swiss
    and New Zealand postcodes are 4 digits too.
    """
    name = " ".join(text.split()).casefold()
    if name in NAME_TO_STATE:
        return NAME_TO_STATE[name]
    if name in NO_STATE_GIVEN:
        return state_from_postcode(postcode)
    return State.OVERSEAS
