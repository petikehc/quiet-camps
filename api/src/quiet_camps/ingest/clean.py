from datetime import date, datetime


def normalise(name: str) -> str:
    """Compare column names across variants: 'Stay Date', 'stay_date', 'STAY_DATE '."""
    return name.strip().lower().replace("_", " ")


def parse_date(text: str) -> date:
    """'1/07/2019' or '1/07/2019 0:00' → date. Raises ValueError for anything else.

    Temporary: only the most common format. Task 3c replaces it with one that handles all five.
    """
    return datetime.strptime(text.split(" ")[0], "%d/%m/%Y").date()
