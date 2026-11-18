# Quiet Camps

Find Queensland campgrounds that are usually quiet on your dates, from public QPWS camping-permit data. A learning project: Python (FastAPI, SQLAlchemy 2.0, Alembic, Postgres) with a React + TypeScript front end.

## Layout

- `api/`: uv project, src layout (`src/quiet_camps/`), tests in `api/tests/`
- `web/`: Vite + React + TypeScript (later)
- `docker-compose.yml`: Postgres 18
- `docs/adr/`: architecture decisions (copy `0000-template.md`)

## Commands (run in `api/`)

```sh
uv run ruff check && uv run ruff format --check && uv run pyright && uv run pytest
```

`docker compose up -d --wait` from the repo root starts Postgres. The migration tests need it; they use their own `quiet_camps_test` database. `uv run alembic upgrade head` migrates the local database.

## How we work

- Use the `learning-project` skill. Coding mode: **the learner writes every 🧑‍💻 task** (anything that teaches a Python learning-path item). Claude writes 🤖 tasks (config, Docker, CI, most of the React).
- For a 🧑‍💻 task: explain the concept compared with TypeScript/Node, give the brief, the files to touch and a failing test Claude wrote. One task at a time, 20–60 minutes. Hints only when asked: nudge → concept → pseudo-code → solution. Never edit the learner's code unasked.
- Review: correct, idiomatic, pyright-strict clean, tested, plus one "senior would" note. The learner makes the fixes; Claude runs all four checks, then commits.
- Every step is verified with real output and includes one negative check.

## Git

- Branch per phase (`feat/ingest`, `feat/db`, `feat/api`, `feat/web`, `feat/ship`), one conventional commit per step, a PR at the end of each phase that the owner merges.
- Ask before every `git push`; one yes covers one push.
- Commits use the GitHub noreply email set in this repo's git config.

## Data

- Camping permits: data.qld.gov.au, CC BY 4.0. Fetched at run time into `data/` (gitignored), never committed.
- No campsite capacity and no coordinates in the data: "quiet" is relative to each campground's own history.
