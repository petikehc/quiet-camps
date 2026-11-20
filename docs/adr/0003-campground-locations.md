# 0003: Campground locations from OpenStreetMap, checked against park outlines

- **Status:** accepted
- **Date:** 2026-11-20

## Context

The permit data names a park and a camping area, with no coordinates. A map and any "near me" search need a point for each of the 830 campgrounds (548 booked since 2024). The sources available:

- **OpenStreetMap:** 1,476 named campsites in Queensland (`tourism=camp_site`), named by volunteers ("Spicer's Gap Campground - Main Range NP", "Cape Creak"). Licensed under the ODbL.
- **Protected areas of Queensland:** 1,010 park outlines, each with a centre point (CC BY 4.0, data from 2022). They have no recreation areas or Great Walks, and those are the busiest places: K'gari, Cooloola, Inskip.
- No official dataset of campground locations exists that we could find.

Names alone mislead. "Stinson remote bush camp" in Lamington matched "Stinson Memorial Park", 2 km outside the park. "Simpson Desert" matched a roadhouse. Two OSM points share the name "Wairuna", 5 km apart.

## Decision

`qc locations --fetch` downloads both sources to `data/locations/` (never committed). Matching then runs from those files, also at the end of `qc load` and `qc refresh`:

1. **Anchors:** a campground whose name has exactly one strong OSM match (≥ 95) anywhere in Queensland. The middle of a park's anchors is its centre. This locates parks that have no outline, and the outlines its anchors fall in become that park's outlines (K'gari → Great Sandy NP). Parks without anchors use the official centre.
2. **Match** the rest by name within 50 km of the park centre. A word-based score of 85 or more counts. The campground rules' key is reused, with words that aren't the place dropped (bush, walkers, day use). Numbers and compass words must agree ("noosa river 1" ≠ "13"), and a name with no place word ("Camp 1") never matches.
3. **Reject** a match that is more than 1 km outside the park's outlines, at a business (roadhouse, retreat, caravan park…), or tied with an equally good match more than 1 km away. A rejected campground falls back to its park centre. A business never causes a tie, and an exact name beats one that only contains it.
4. **Flag** anything not straightforward in `campground.location_flags`: `weak_name`, `contains`, `tie`, `shared_point`, `edge_of_park`, `no_park_outline`, `rejected_osm`, `reviewed`. `location_source` says where the point came from: `osm`, `park_osm` (centre of the anchors, so also OSM data), `park_qld` or `manual`. `osm_type` and `osm_id` link every match, or rejected match, to openstreetmap.org.
5. **Overrides:** `location_overrides.csv` picks an OSM campsite, sets coordinates, or rejects a match, after someone has reviewed it. `qc locations` prints the counts, every flagged campground in use, and (`--sample N`) clean matches to check by hand.

Outlines are stored as GeoJSON in `jsonb`: every park in `park_outline`, simplified to about 100 m (1.2 MB). OSM's own outline goes in `campground.osm_outline` for the 43 matched campsites drawn as an area. Point-in-polygon and distance-to-edge are about 100 lines of plain Python (`quiet_camps.ingest.geo`).

## Alternatives considered

- **Scope the match by park outline, with park names mapped to outlines:** fails exactly where it matters most, because recreation areas and Great Walks have no outline, and permit park names don't follow the official names.
- **A radius from the park's area (a circle the same size):** far too small for long parks and island groups. K'gari's radius came out as 0 km, because its name matched a 34 ha state forest.
- **Trust names only:** in the prototype, the outline check caught 7 wrong matches that had read as plausible (Stinson, Darlington, Cordalba → Hinchinbrook Island, Platypus Bay → Danbulla).
- **PostGIS:** the right tool once SQL needs spatial queries ("campgrounds within 50 km"). For now it would mean a new Docker image and an extension, for checks that run once per refresh in Python.
- **Geocoding services:** not built for bush camps; usage terms and rate limits for a bulk job.

## Consequences

Measured on 20 Nov 2026 over the 548 campgrounds booked since 2024:

| Source | Campgrounds | Share of booked sites |
|---|---|---|
| `osm` | 261 (48%) | 65% |
| `park_osm` | 184 (34%) | 29% |
| `park_qld` | 103 (19%) | 5% |

- 143 are clean matches. 127 carry a flag; most are `shared_point` (one campsite under two names, such as a Great Walk camp and the park's camp at the same place) or `contains`. 10 are rejected, including 7 ties between equally named points the data can't settle.
- **Error rate:** 30 clean matches chosen at random all agreed by name and lay inside the right park, with no competing candidate. Zero errors in 30 puts the error rate among clean matches below about 10% with 95% confidence (rule of three). This was checked against names and outlines, not on the ground. An exact name with a single candidate could still be the wrong place.
- **The map should show the difference:** a solid pin for a clean match, an outlined pin with the reasons for flagged ones, a faded park-centre marker otherwise. The API returns `location_source` and `location_flags` for that.
- **ODbL:** points, OSM outlines and `park_osm` centres are OSM-derived. Showing them on a map or in a list needs "© OpenStreetMap contributors". Publishing the matched database itself (not just a map or app built on it) would require sharing it under the ODbL.
- The official outlines are from 2022, so newer parks and renames (K'gari, Apudthama) are missing or under old names; anchors work around most of it. A new OSM fetch can change matches. Re-run `qc locations` and review the flagged list before trusting it.
