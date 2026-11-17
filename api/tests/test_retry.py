from typing import assert_type

import pytest

from quiet_camps.ingest.retry import retry


class Flaky:
    """A stand-in for a network call: fails `failures` times, then succeeds."""

    def __init__(self, failures: int, error: BaseException | None = None) -> None:
        self.failures = failures
        self.error = error or ConnectionError("connection reset")
        self.calls = 0

    def __call__(self, name: str, *, size: int = 1) -> str:
        self.calls += 1
        if self.calls <= self.failures:
            raise self.error
        return f"{name}:{size}"


def test_retries_then_succeeds_with_doubling_delays() -> None:
    sleeps: list[float] = []
    flaky = Flaky(failures=2)
    fetch = retry(attempts=3, delay=1.0, sleep=sleeps.append)(flaky)

    result = fetch("camping.csv", size=9)

    assert_type(result, str)  # checked by pyright: the wrapper keeps the return type
    assert result == "camping.csv:9"
    assert flaky.calls == 3
    assert sleeps == [1.0, 2.0]


def test_gives_up_after_the_last_attempt_and_raises_its_error() -> None:
    sleeps: list[float] = []
    flaky = Flaky(failures=5)
    fetch = retry(attempts=3, delay=0.5, sleep=sleeps.append)(flaky)

    with pytest.raises(ConnectionError):
        fetch("camping.csv")

    assert flaky.calls == 3
    assert sleeps == [0.5, 1.0]  # no pointless sleep after the final failure


def test_does_not_retry_when_retry_if_says_no() -> None:
    sleeps: list[float] = []
    flaky = Flaky(failures=1, error=FileNotFoundError("404"))
    fetch = retry(
        attempts=3,
        retry_if=lambda exc: not isinstance(exc, FileNotFoundError),
        sleep=sleeps.append,
    )(flaky)

    with pytest.raises(FileNotFoundError):
        fetch("missing.csv")

    assert flaky.calls == 1
    assert sleeps == []


def test_never_retries_ctrl_c() -> None:
    sleeps: list[float] = []
    flaky = Flaky(failures=1, error=KeyboardInterrupt())
    fetch = retry(attempts=3, sleep=sleeps.append)(flaky)

    with pytest.raises(KeyboardInterrupt):
        fetch("camping.csv")

    assert flaky.calls == 1


def test_zero_attempts_is_rejected() -> None:
    flaky = Flaky(failures=0)
    fetch = retry(attempts=0)(flaky)

    with pytest.raises(ValueError, match="at least 1"):
        fetch("camping.csv")

    assert flaky.calls == 0


def test_works_with_decorator_syntax_and_keeps_the_function_name_and_docstring() -> None:
    sleeps: list[float] = []

    @retry(sleep=sleeps.append)
    def download(name: str) -> str:
        """Download one file."""
        return name

    assert download("camping.csv") == "camping.csv"
    assert download.__name__ == "download"
    assert download.__doc__ == "Download one file."
