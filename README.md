# Quiet Camps

Find Queensland campgrounds that are usually quiet on your dates.

A learning project with Python (FastAPI, SQLAlchemy, Postgres) and React, built on ten years of public camping-permit data from Queensland Parks and Wildlife Service.

> **Work in progress.** This README grows with the project.

## Data and attribution

- Camping permits: [Camping and vehicle permits](https://www.data.qld.gov.au/dataset/camping-and-vehicle-permits), © State of Queensland, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- Campground locations: © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors, available under the [Open Database Licence](https://opendatacommons.org/licenses/odbl/).
- Park outlines: [Protected areas of Queensland](https://www.data.qld.gov.au/dataset/protected-areas-of-queensland-series), © State of Queensland, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- The data shows **past bookings**, not live availability. "Quiet" means quiet compared with that campground's own history.

This project is not affiliated with or endorsed by Queensland Parks and Wildlife Service or the Queensland Government.

## Run it locally

```sh
docker compose up -d   # Postgres 18

cd api
uv run alembic upgrade head
uv run qc download && uv run qc load   # the permits from data.qld.gov.au
uv run qc locations --fetch            # campground locations from OSM and park outlines
uv run uvicorn quiet_camps.api.app:create_app --factory --port 8000

cd ../web
pnpm install && pnpm dev               # http://localhost:5173
```

The API documents itself at http://localhost:8000/docs. The web client's types are
generated from that contract: see [web/README.md](web/README.md).

## How it was built

Built step by step with [Claude Code](https://claude.com/claude-code) under my direction. I wrote the Python learning pieces myself; the README will say which parts are which.
