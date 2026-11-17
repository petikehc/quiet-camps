import functools
import time
from collections.abc import Callable


def retry[**P, R](
    *,
    attempts: int = 3,
    delay: float = 1.0,
    retry_if: Callable[[Exception], bool] = lambda exc: True,
    sleep: Callable[[float], None] = time.sleep,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            for attempt in range(1, attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:
                    if attempt == attempts or not retry_if(exc):
                        raise
                    sleep(delay * 2 ** (attempt - 1))
            raise ValueError("attempts must be at least 1")

        return wrapper

    return decorator
