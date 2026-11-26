"""Which QPWS page a campground links to: its camping area's page, else its park's.

Names are compared like OSM names (see quiet_camps.ingest.locations). QPWS adds a section after
a comma ("Alligator Creek camping area, Mount Elliot"), so only the part before it counts.

1. A page in our park needs MATCH_SCORE; one in another park needs a near-exact name.
2. The best is in our park, then has the best score, then the closest full area key
   ("central station", not "central station great walk").
3. Pages still tied in our park are one place listed twice (tent and trailer sites): the
   first, by URL. Tied elsewhere, none of them.
4. With no camping page, the park's page, when exactly one park page has our park key.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from rapidfuzz import fuzz

from quiet_camps.ingest.campgrounds import area_key, park_key
from quiet_camps.ingest.locations import ANCHOR_SCORE, MATCH_SCORE, match_key, name_score
from quiet_camps.ingest.qpws import CampingPage, ParkPage

type Rank = tuple[bool, float, float]  # (in our park, name score, full area key ratio)


@dataclass(frozen=True)
class QpwsLink:
    url: str
    kind: Literal["camping", "park"]


def qpws_link(
    park: str, name: str, camping: Sequence[CampingPage], parks: Sequence[ParkPage]
) -> QpwsLink | None:
    ours, our_park = match_key(name), park_key(park)
    our_area = area_key(name.split(" - ")[0])
    candidates: list[tuple[Rank, str]] = []
    for page in camping:
        their_name = page.name.split(",")[0]
        score = name_score(ours, match_key(their_name))
        same_park = park_key(page.park_name) == our_park
        if score >= (MATCH_SCORE if same_park else ANCHOR_SCORE):
            rank = (same_park, score, fuzz.ratio(our_area, area_key(their_name)))
            candidates.append((rank, page.url))
    if candidates:
        best = max(rank for rank, _ in candidates)
        top = sorted(url for rank, url in candidates if rank == best)
        in_our_park = best[0]
        if len(top) == 1 or in_our_park:
            return QpwsLink(top[0], "camping")

    urls = {p.url for p in parks if park_key(p.name) == our_park}
    return QpwsLink(urls.pop(), "park") if len(urls) == 1 else None
