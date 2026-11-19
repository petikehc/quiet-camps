"""One campground, many names: park renames, rewording, and tent/trailer/group splits.

"Dundubara (Tent Site) camping area" in "Fraser Island Recreation Area" and "Dundubara camping
area" in "K'gari (Fraser Island) Recreation Area" are the same place. Rules turn each name
into a key, a reviewed CSV merges the keys the rules miss, and fuzzy matching only suggests
rows for that CSV: place names that differ by one character are often different places.
"""

import csv
import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from rapidfuzz import fuzz

type Key = tuple[str, str]  # (park key, area key)

MERGES_CSV = Path(__file__).with_name("campground_merges.csv")

# The kind of park, not the place: "Byfield State Forest" and "Byfield National Park" are one.
PARK_WORDS = re.compile(
    r"national parks?|\bnp\b|conservation park|regional park|state forests?|forest reserve"
    r"|resources? reserves?|recreation area|great walk|remote bush camping|\band\b"
)
# Renames and regroupings, from the key the rules give to the key it belongs with.
PARK_ALIASES = {
    "fraser island": "kgari",
    "d aguilar": "daguilar",
    "carnarvon gorge": "carnarvon",
    "mount moffatt": "carnarvon",
    "ka ka mundi carnarvon": "carnarvon",
    "salvator rosa carnarvon": "carnarvon",
    "davies creek": "davies creek dinden",
    "dinden": "davies creek dinden",
    "davies creek merged into davies creek dinden oct 2013": "davies creek dinden",
    "thorsborne trail": "hinchinbrook island",
    "heathlands": "jardine river heathlands",
    "jardine river": "jardine river heathlands",
    "apudthama": "jardine river heathlands",  # renamed Apudthama National Park (CYPAL) in 2025
    "glen rock": "main range",  # Glen Rock State Forest joined Main Range in April 2023
    "misty mountains trails": "misty mountains wilderness tracks",
    "mouth of baffle creek 2": "mouth of baffle creek",
    "mangkalba": "ngalba bulal",
    "snapper island": "hope islands",
    "goldsmith island": "smith islands",
    "murray falls": "girramay",
    "cape tribulation": "daintree",
    "broadwater": "abergowrie",
}
# The kind of site, booking or status, not the place. Tent, trailer and group sites count
# as one campground: the 2025 data merged them anyway. Longer phrases come first.
AREA_WORDS = re.compile(
    r"camping areas?|camping zones?|camp ?grounds?|campgound|camp ?sites?|camping|\bcamp\b"
    r"|\bareas?\b|\bsites?\b|\btent\b|trailer or van|\btrailer\b|\bgroup\b|\bedu\b|\bpwd\b|\bcto\b"
    r"|commercial operator|\bremote\b|\bold\b|obsolete|obselete|\bobsel\b|temp closure"
    r"|otr closed|\bclosed\b|not for (use by )?ssq( use)?|\bincluding\b"
)
# Two names that differ in any of these are different places, however similar they look:
# "noosa river 1" and "13", "north kobble" and "south kobble", "harrys hut a" and "b".
DISTINGUISHING = re.compile(
    r"\d+|\b\w*(north|south|east|west)\w*\b|\b(upper|lower|top|bottom)\b|\b[a-z]\b"
)


def _clean(text: str, words: re.Pattern[str]) -> str:
    text = re.sub(r"(?<=[a-z])(?=[A-Z]{2})", " ", text)  # "camping areaOLD" → "camping area OLD"
    text = text.casefold()
    # "Garry's", "Garry\u2019s" (curly), "Garry?s" and "Garry\x92s" (cp1252) are one name.
    text = re.sub(r"(?<=[a-z])['\u2019?\x92](?=[a-z])", "", text)
    text = re.sub(r"\.", "", text)  # "M.V. Sarawak" → "mv sarawak"
    text = re.sub(r"\bmt\b", "mount", text)
    text = words.sub(" ", text)
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    return " ".join(text.split())


def park_key(park: str) -> str:
    """'K'gari (Fraser Island) Recreation Area' → 'kgari'."""
    # Brackets hold an old name, a parent park or a district; after a comma or dash comes a
    # trail. None of them is the park itself.
    park = re.sub(r"\(.*?\)", " ", park)
    park = re.split(r",| - |/", park)[0]
    key = _clean(park, PARK_WORDS)
    return PARK_ALIASES.get(key, key)


def area_key(area: str) -> str:
    """'Dundubara (Tent Site) camping area' → 'dundubara'."""
    return _clean(area, AREA_WORDS)


def load_merges(path: Path = MERGES_CSV) -> dict[Key, Key]:
    """The reviewed merges: {(park, area): (park, same_as)}, all written as keys."""
    with path.open(newline="", encoding="utf-8") as f:
        return {
            (row["park"], row["area"]): (row["park"], row["same_as"]) for row in csv.DictReader(f)
        }


def campground_key(park: str, area: str, merges: dict[Key, Key]) -> Key:
    key = (park_key(park), area_key(area))
    return merges.get(key, key)


@dataclass(frozen=True)
class Suggestion:
    score: float
    park: str
    area: str
    same_as: str


def suggest_merges(keys: Iterable[Key], threshold: float = 85.0) -> list[Suggestion]:
    """Pairs of area keys in the same park that look like one place, best match first.

    Only suggestions: someone reads each one before it goes in the merges CSV.
    """
    by_park: dict[str, set[str]] = defaultdict(set)
    for park, area in keys:
        by_park[park].add(area)

    suggestions: list[Suggestion] = []
    for park, areas in by_park.items():
        ordered = sorted(areas)
        for i, area in enumerate(ordered):
            for other in ordered[i + 1 :]:
                if _markers(area) != _markers(other):
                    continue
                score = fuzz.ratio(area, other)
                if score >= threshold:
                    suggestions.append(Suggestion(score, park, area, other))
    return sorted(suggestions, key=lambda s: (-s.score, s.park, s.area))


def _markers(area: str) -> set[str]:
    return {m.group(0) for m in DISTINGUISHING.finditer(area)}
