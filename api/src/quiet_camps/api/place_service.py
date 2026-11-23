"""Places by name, for "near Noosa" and "from Toowoomba": the ABS's suburbs and council areas,
and our parks and campgrounds."""

from dataclasses import dataclass
from typing import Protocol

from rapidfuzz import fuzz, process, utils

# Names are compared word by word (token_set_ratio): "sunny coast" → Sunshine Coast (80),
# "the gold coast" → Gold Coast (100). WRatio, tried first, preferred long names holding any
# of the words ("sunny coast" → Burrum Coast National Park). A name scoring this or more is
# the place someone meant; below it, it's a guess ("tweed" → Woree, 60).
MATCH_SCORE = 80
# Equally good matches: the broader place first, so "Noosa" is the council area, not a camp.
BROADEST_FIRST = {"council": 0, "locality": 1, "park": 2, "campground": 3}


@dataclass(frozen=True, kw_only=True)
class Place:
    name: str
    kind: str  # council, locality, park or campground
    lat: float
    lon: float


@dataclass(frozen=True, kw_only=True)
class PlaceMatch:
    place: Place
    score: float  # 0-100


class PlaceSource(Protocol):
    async def places(self) -> list[Place]: ...


def matches(places: list[Place], q: str, limit: int) -> list[PlaceMatch]:
    """The places whose names best match q, best first."""
    found = process.extract(
        q,
        [p.name for p in places],
        scorer=fuzz.token_set_ratio,
        processor=utils.default_process,
        limit=None,
        score_cutoff=50,
    )
    ranked = sorted(
        (PlaceMatch(place=places[i], score=score) for _, score, i in found),
        key=lambda m: (-m.score, BROADEST_FIRST[m.place.kind], m.place.name),
    )
    return ranked[:limit]


async def search_places(source: PlaceSource, q: str, limit: int) -> list[PlaceMatch]:
    return matches(await source.places(), q, limit)


async def find_place(source: PlaceSource, name: str) -> Place | None:
    """The place someone meant by name, or None when nothing matches well enough."""
    best = matches(await source.places(), name, 1)
    return best[0].place if best and best[0].score >= MATCH_SCORE else None
