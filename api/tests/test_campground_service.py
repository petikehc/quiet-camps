"""The campground service on its own: a fake source stands in for the database."""

import asyncio
from datetime import date, timedelta

import pytest

from quiet_camps.api.campground_service import (
    CampgroundDetail,
    CampgroundNotFound,
    get_campground,
)
from quiet_camps.db.locations import ACTIVE_SINCE
from quiet_camps.db.models import Campground


class FakeSource:
    """Satisfies CampgroundSource by shape alone: it never names it."""

    def __init__(self, *campgrounds: Campground) -> None:
        self.campgrounds = {c.id: c for c in campgrounds}

    async def get(self, campground_id: int) -> Campground | None:
        return self.campgrounds.get(campground_id)


def campground(campground_id: int = 7, last_night: date | None = date(2025, 3, 11)) -> Campground:
    # A transient ORM object: no session, no database.
    return Campground(
        id=campground_id,
        name="Quiet Creek camping area",
        park_name="Test Range National Park",
        last_night=last_night,
        lat=-28.2,
        lon=153.1,
        location_source="osm",
        location_flags=["weak_name"],
    )


def detail(*campgrounds: Campground, campground_id: int = 7) -> CampgroundDetail:
    return asyncio.run(get_campground(FakeSource(*campgrounds), campground_id))


def test_returns_the_campgrounds_fields() -> None:
    assert detail(campground()) == CampgroundDetail(
        id=7,
        name="Quiet Creek camping area",
        park_name="Test Range National Park",
        last_night=date(2025, 3, 11),
        active=True,
        lat=-28.2,
        lon=153.1,
        location_source="osm",
        location_flags=["weak_name"],
    )


def test_booked_on_the_first_active_night_is_active() -> None:
    assert detail(campground(last_night=ACTIVE_SINCE)).active


def test_booked_only_before_then_is_retired() -> None:
    assert not detail(campground(last_night=ACTIVE_SINCE - timedelta(days=1))).active


def test_never_booked_is_retired() -> None:
    assert not detail(campground(last_night=None)).active


def test_an_unknown_id_is_not_found() -> None:
    with pytest.raises(CampgroundNotFound) as raised:
        detail(campground(campground_id=7), campground_id=8)

    assert raised.value.campground_id == 8
