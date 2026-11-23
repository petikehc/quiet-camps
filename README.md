# Quiet Camps

Queensland camping since 2011, read from the permits: where people travel from, when the crowds arrive, and which campgrounds are usually quiet on your dates.

A learning project with Python (FastAPI, SQLAlchemy, Postgres) and React, built on every public camping permit since 2011 from Queensland Parks and Wildlife Service.

> **Work in progress.** This README grows with the project.

## Data and attribution

- Camping permits: [Camping and vehicle permits](https://www.data.qld.gov.au/dataset/camping-and-vehicle-permits), © State of Queensland, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- Campground locations: © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors, available under the [Open Database Licence](https://opendatacommons.org/licenses/odbl/).
- Park outlines: [Protected areas of Queensland](https://www.data.qld.gov.au/dataset/protected-areas-of-queensland-series), © State of Queensland, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- Postcode centres, suburbs and localities, and council areas: [ABS Australian Statistical Geography Standard 2021](https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs-edition-3), © Commonwealth of Australia, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- Queensland state school holidays, 2026 to 2029: [Department of Education](https://education.qld.gov.au/about-us/calendar/term-dates), © State of Queensland. Kept as a short reviewed list in `api/src/quiet_camps/ingest/qld_school_holidays.csv`.
- The data shows **past bookings**, not live availability. "Quiet" means quiet compared with that campground's own history.

This project is not affiliated with or endorsed by Queensland Parks and Wildlife Service or the Queensland Government.

## Run it locally

```sh
docker compose up -d   # Postgres 18

cd api
uv run alembic upgrade head
uv run qc download && uv run qc load   # the permits from data.qld.gov.au
uv run qc locations --fetch            # campground locations from OSM and park outlines
uv run qc postcodes --fetch            # where campers come from, for the homepage's map
uv run qc places --fetch               # Queensland towns and council areas, to search near
uv run uvicorn quiet_camps.api.app:create_app --factory --port 8000

cd ../web
pnpm install && pnpm dev               # http://localhost:5173
```

The site has a homepage (a year of camping trips on a night map), an explorer at `/explore`
(a full-screen map of the campgrounds that are usually quiet, not too busy or busy on your
dates, near a place if you like) and a page per campground.

The API documents itself at http://localhost:8000/docs. The web client's types are
generated from that contract: see [web/README.md](web/README.md).

### Plain-words search (optional, AWS)

"Where and when?" boxes send what you type to `POST /ask`, which reads it with Claude Haiku 4.5
on Amazon Bedrock ([ADR 0005](docs/adr/0005-natural-language-search-on-bedrock.md)). It's off
unless switched on, and the site works without it: the dates and place can always be set by
hand.

1. An AWS account with Amazon Bedrock, and a profile on this machine whose identity may call
   `bedrock:InvokeModel` on the `au.anthropic.claude-haiku-4-5-20251001-v1:0` inference
   profile (Sydney, keeping the words in Australia).
2. `cp api/.env.example api/.env`, set `AWS_PROFILE`, then start the API with
   `--env-file .env`.
3. Set a budget alert, so a surprise is an email, not a bill: AWS console → Billing and Cost
   Management → Budgets → Create budget → Monthly cost budget, e.g. US$5, with your email.

Each new phrasing is one call, about a tenth of a US cent; the same words again that day come
from a cache. The API allows 20 asks an hour per client, and never stores or logs the words.

## How it was built

Built step by step with [Claude Code](https://claude.com/claude-code) under my direction. I wrote the Python learning pieces myself; the README will say which parts are which.
