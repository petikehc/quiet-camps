# 0004: Async SQLAlchemy in the API, and when a route is a plain `def`

- **Status:** accepted
- **Date:** 2026-11-20

## Context

The API (FastAPI) reads the database on almost every request. Everything written before it is synchronous: the loaders, `qc refresh`, and the campground and location code use sync psycopg and SQLAlchemy, because they run as batch jobs with nothing else waiting.

FastAPI runs an `async def` route on the event loop, which has one thread, and a plain `def` route in a thread pool (AnyIO's default limit is 40 threads). A sync call that waits on I/O inside `async def` holds the loop, so every other request waits too. Nothing fails, and a test with one request at a time can't show it.

To measure the difference, three endpoints wait 0.1 s each (`/experiment/*`, mounted only with `EXPERIMENTS=true`). They were loaded with oha against one uvicorn process on a MacBook, with `/health` (a `SELECT 1`) timed during each run:

| Endpoint | Concurrent | Requests/s | p50 | `/health` during the load |
|---|---|---|---|---|
| `async def` + `time.sleep` | 50 | 9.6 | 5.09 s | 20.3 s |
| `def` + `time.sleep` | 50 | 374 | 109 ms | 2 ms |
| `async def` + `await asyncio.sleep` | 50 | 479 | 104 ms | 3 ms |
| `def` + `time.sleep` | 200 | 379 | 523 ms | 3 ms |
| `async def` + `await asyncio.sleep` | 200 | 1,913 | 102 ms | 2 ms |

Each matches its ceiling: requests that can wait at once ÷ 0.1 s, that is 1, 40 threads, or every connection.

## Decision

- **The API uses async SQLAlchemy** (`create_async_engine`, `async_sessionmaker`) with psycopg 3's async mode, on the same `postgresql+psycopg://` URL. `create_app` makes one engine per app. `get_session` is a dependency with `yield` that gives each request a session and closes it after the route, even when the route raises.
- **Batch code stays sync.** The CLI loads and refreshes run one at a time; async would add complexity and no throughput.
- **Choosing `async def` or `def` for a route or dependency:**
  - only awaited async I/O → `async def`
  - any sync I/O (sync psycopg or SQLAlchemy, `requests`, `time.sleep`, large file reads) → plain `def`
  - async with one sync call → `async def`, with that call in `await asyncio.to_thread(...)`
  - heavy CPU work → neither fixes it; precompute it or move it out of the request
- **Ruff's `ASYNC` rules are on.** They flag the standard-library cases (`time.sleep`, blocking HTTP, `open()` inside `async def`). They can't see a sync database call, so review checks those.

## Alternatives considered

- **Sync SQLAlchemy in plain `def` routes:** reuses the existing query code as it is, and is safe. But throughput is capped by the thread pool: 379 requests/s against 1,913 at 200 concurrent requests, with p50 growing from 102 ms to 523 ms as requests queue for threads. Raising the thread limit trades that for memory and more connections.
- **asyncpg instead of psycopg's async mode:** faster in benchmarks, but a second driver with different types and errors, while psycopg 3 already serves both the sync batch code and the async API.
- **Async everywhere, including the loaders:** no gain for jobs that run one at a time, and a rewrite of tested code.

## Consequences

- **Query code can't be shared directly** between the sync batch code and async routes. A route that needs existing sync code either becomes a plain `def` or calls it with `asyncio.to_thread`. Pure functions (no I/O) can be shared freely.
- **Tests use `with TestClient(app)`,** so every request in a test runs on one event loop. Pooled async connections belong to the loop that opened them.
- **The pool recovers by itself:** with Postgres stopped under a running server, `/health` went 200 → 503 → 200 when it came back, without a restart.
- **Watch for:** sync calls creeping into `async def` (ruff catches only the standard-library ones), and the 40-thread limit if any plain `def` route gets busy.
- **Reproducing the numbers** (macOS accepts at most 128 waiting connections, `kern.ipc.somaxconn`, so short runs at 200 concurrent requests include 1 s TCP retries; run at least a few thousand requests):

  ```sh
  cd api && EXPERIMENTS=true uv run uvicorn quiet_camps.api.app:create_app --factory
  oha -n 6000 -c 200 --no-tui http://127.0.0.1:8000/experiment/async-sleep
  ```
