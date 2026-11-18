import re
from datetime import date, datetime, timedelta

# Each format only matches its own shape ("%d/%m/%y" rejects "1/07/2016" and "%d/%m/%Y"
# rejects "01/07/15"), so the order doesn't matter.
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
            return datetime.strptime(value, date_format).date()
        except ValueError:
            continue

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
