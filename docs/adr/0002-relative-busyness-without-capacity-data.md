# 0002: Relative busyness without capacity data

- **Status:** accepted
- **Date:** 2026-11-19

## Context

The permit data says who booked which camping area on which night. It doesn't say how many sites an area has, so "70% full" can't be computed. The app's question is narrower: **is this campground usually quiet on these nights, compared with its own history?** Answering it needs four things the raw rows don't give directly:

1. **Each booking counted once.** Quarterly files overlap: a stay that crosses a quarter boundary appears, every night of it, in both quarters' files. The 2025–26 files have no reservation ID, and there the overlap doubled quarter-end nights (31 Dec 2025: 6,357 raw sites, 3,200 real).
2. **One history per campground.** One place appears under many names over 15 years: park renames (Fraser Island became K'gari), rewording, letter case, and tent, trailer and group sites that merged in 2025. Dundubara had 19 names. Before merging, 28% of the last 12 months' bookings were at names with less than 2.5 years of history.
3. **Like compared with like.** Saturdays are about twice as busy as Tuesdays, and Easter moves between 22 March and 25 April.
4. **Quiet told apart from closed.** Only booked nights exist. Cape York campgrounds have no bookings from December to May (wet season), and camping closed from 26 March to 31 May 2020 (COVID).

## Decision

Three derived layers, rebuilt by `qc refresh` (and at the end of `qc load`):

- **`area_night`** (materialised view): sites and campers per camping area per night. A booking-night is keyed on **every field except the source file** (area, night, reservation ID, booking date, party size, postcode, state). Rows are counted per file, because identical rows in one file are separate sites. The largest count across files is kept, and the results are summed per area and night.
- **`campground`**: every camping-area name maps to one campground through rules (park aliases, words such as "camping area" or "(Tent Site)" dropped, spelling variants) and a reviewed `campground_merges.csv`. Fuzzy matching (`qc campgrounds`) only suggests rows for that file, and never across a number or compass word. 1,448 names become 830 campgrounds. `last_night` marks retired ones: 304 campgrounds have had no booking since 2024.
- **`campground_typical`** (materialised view): per campground and **kind of night**, the median sites, the median campers, the number of past nights used, and **busyness**.
  - Kinds of night come from `calendar_day`. An ordinary night is an ISO week plus weekday ("week 14 6"). The nights of a Queensland public-holiday long weekend are that holiday plus an offset ("easter +1"), so Easter compares with Easter. 24 Dec to 2 Jan is matched by calendar date.
  - An unbooked night counts as **0 sites, but only in a month the campground had a booking that year**. A month with none is left out as closed or unknown. The COVID closure and the latest quarter (still filling with bookings) are left out.
  - **busyness = typical sites ÷ the campground's 95th-percentile night (at least 1 site)**. 1.0 means "as busy as its usual busy nights". It doesn't mean "full".

## Alternatives considered

- **Deduplicate on the reservation ID only, falling back to the fingerprint without one:** exact for rows with an ID, but twice the SQL, to fix 319 of 4.6M sites with an ID.
- **Fuzzy matching that merges names automatically:** place names that differ by one character are often different places ("noosa river 1" and "13" score 96, "north" and "south kobble" 92).
- **Merging Teewah Beach's zones 1–7 (since 2021) back into one beach:** gives 15 years of history instead of 5, but a camper picks a zone.
- **Typical night by calendar date or by month:** mixes weekdays, and blurs Easter across five weeks.
- **Counting every unbooked night as 0:** closed seasons would look perfectly quiet.
- **Counting only booked nights:** small campgrounds would never look quiet, because their empty nights disappear.
- **Campers instead of sites as the measure:** campers is closer to how crowded a place feels, but a few large groups swing it, and some 2025–26 rows have no party size.

## Consequences

- A search is one join: the nights asked for → `calendar_day.kind` → `campground_typical`, filtered to campgrounds with a recent `last_night` and enough past nights. It takes about 3 ms over 830 campgrounds.
- **Known limits:**
  - Where two files describe the same booking differently, both copies count (+319 of 4.6M sites with an ID).
  - For rows without an ID, identical rows within one file are assumed to be separate sites. This is checked for rows with an ID, not for rows without.
  - School holidays are only matched approximately, by ISO week.
  - A closure that starts mid-month counts its closed nights as 0.
- `campground_merges.csv` needs a look after each new quarter's data. `qc campgrounds` lists the new candidates.
- Busyness compares a campground only with itself. A remote camp at 1.0 may hold four tents, and a K'gari campground at 0.5 may hold eighty.
