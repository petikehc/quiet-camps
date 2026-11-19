import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass


@dataclass
class Elapsed:
    """Filled in when the with-block ends, so read it after the block, not inside it."""

    seconds: float = 0.0


@contextmanager
def timed(clock: Callable[[], float] = time.perf_counter) -> Generator[Elapsed]:
    """Time a with-block, even one that raises: `with timed() as t: ...`, then `t.seconds`."""
    elapsed = Elapsed()
    start = clock()
    try:
        yield elapsed
    finally:
        elapsed.seconds = clock() - start
