import dataclasses
from datetime import date

from quiet_camps.ingest.clean import State
from quiet_camps.ingest.parse import CampNight
from quiet_camps.ingest.quality import night_warnings

COMPLETE = CampNight(
    night=date(2022, 7, 1),
    park="Dalrymple National Park",
    area="Burdekin River camping area",
    adults=2,
    children=0,
    infants=0,
    postcode="4740",
    state=State.QLD,
    booked_on=date(2022, 6, 1),
)
BLANK = dataclasses.replace(COMPLETE, adults=None, postcode=None, state=State.UNKNOWN)


def test_a_blank_night_lists_every_problem() -> None:
    assert night_warnings(BLANK) == ["no party size", "no postcode", "unknown state"]


def test_a_complete_night_has_no_warnings() -> None:
    assert night_warnings(COMPLETE) == []


def test_warnings_for_a_whole_file_collect_in_the_list_you_pass() -> None:
    collected: list[str] = []

    night_warnings(BLANK, collected)
    night_warnings(COMPLETE, collected)
    night_warnings(BLANK, collected)

    assert len(collected) == 6
