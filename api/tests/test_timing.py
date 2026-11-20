from collections.abc import Callable

import pytest

from quiet_camps.timing import timed


def fake_clock(*readings: float) -> Callable[[], float]:
    """A clock that returns these readings in turn, so the tests don't depend on real time."""
    it = iter(readings)
    return lambda: next(it)


def test_timed_measures_the_block() -> None:
    with timed(clock=fake_clock(10.0, 12.5)) as elapsed:
        pass
    assert elapsed.seconds == 2.5


def test_timed_still_measures_when_the_block_raises() -> None:
    # A failed file load should still report how long it took before failing.
    with pytest.raises(ValueError, match="bad row"), timed(clock=fake_clock(1.0, 4.0)) as elapsed:
        raise ValueError("bad row")
    assert elapsed.seconds == 3.0


def test_the_default_clock_is_real_time() -> None:
    with timed() as elapsed:
        pass
    assert 0 <= elapsed.seconds < 1
