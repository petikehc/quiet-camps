"""Three ways to wait 0.1 s, to load-test against each other. Mounted only with experiments on."""

import asyncio
import time

from fastapi import APIRouter

SLEEP = 0.1

experiment_router = APIRouter(prefix="/experiment")


@experiment_router.get("/blocking-sleep")
async def blocking_sleep() -> dict[str, float]:
    # Wrong on purpose: a sync wait inside async def holds the event loop's only thread.
    time.sleep(SLEEP)  # noqa: ASYNC251
    return {"slept": SLEEP}


@experiment_router.get("/thread-sleep")
def thread_sleep() -> dict[str, float]:
    # Plain def: FastAPI runs it in the thread pool, so the loop stays free.
    time.sleep(SLEEP)
    return {"slept": SLEEP}


@experiment_router.get("/async-sleep")
async def async_sleep() -> dict[str, float]:
    await asyncio.sleep(SLEEP)
    return {"slept": SLEEP}
