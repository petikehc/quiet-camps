# 0001: One record per camp-night, not per booking

- **Status:** accepted
- **Date:** 2026-11-18

## Context

The 49 camping-permit files from data.qld.gov.au (Jan 2011 to Sep 2026) use 11 header layouts. These fall into three families (`uv run qc profile` gives the full report):

| Family | Files | One row is |
|---|---|---|
| A: Jan 2011 to Jun 2016 | 7 | one booking: start date + days (mixed with vehicle permits) |
| B: Jul 2016 to Dec 2024 | 35 | one site for one night: stay date |
| C: Jan 2025 onwards | 7 | one booking: arrival + departure date |

The app's core question is "how busy is this camping area on this night?". Rebuilding family B's night rows into bookings doesn't work reliably:

- Stays that cross a quarter are split across two files.
- One reservation can hold several sites with different party sizes on the same night.
- The Jan to Mar 2018 file has no reservation ID at all.

## Decision

Every parser yields one `CampNight`: one camping area, one night, with party size, postcode, state, booking date, and the reservation ID when the file has one (`None` otherwise). Families A and C expand each booking into one record per night. Family B maps one row to one record.

## Alternatives considered

- **One record per booking (the original plan):** matches families A and C, but family B would need a cross-file rebuild that can't work for the Jan to Mar 2018 file. Every query would then expand bookings back into nights in SQL.
- **Also store `stay_nights` on each record:** nothing in the app uses length of stay. Where there's an ID, it can be derived in SQL with `COUNT(DISTINCT night)` per reservation.

## Consequences

- Each file is parsed on its own, and nightly occupancy is a plain `GROUP BY area, night`.
- About 2.5 times more rows than bookings (about 6 million). That's fine for Postgres and `COPY`.
- Quarter files overlap: the same reservation-night can appear in two files. Loading must deduplicate on the reservation ID where there is one. Rows without an ID can't be deduplicated, and the count of those overlaps should be reported.
- **Update 2026-11-18, from `qc quality`:** identical rows *within* one file are real. One reservation can hold two sites with the same party size on the same night (`576013` in 2018). So deduplication keeps, for each reservation-night, the **highest count found in any single file**, rather than collapsing to one row or adding files together. At the time of writing there are 136,975 reservation-nights in more than one place and 223,593 identical nights within files (mostly in files without IDs, where duplicates can't be told apart from separate groups with the same details).
- Lead time (booking date to night) is available on every record. Length of stay isn't stored. It can be derived for files with IDs, but not for the Jan to Mar 2018 file.
