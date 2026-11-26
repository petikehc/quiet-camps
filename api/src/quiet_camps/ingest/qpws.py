"""QPWS's own web pages for each camping area and park, from its two A to Z listings.

parks.qld.gov.au answers scripts with a Cloudflare challenge, so the listings come from the
Internet Archive's latest captures. Both lay out an entry the same way:

    <li data-park-id="162357"><h3>
      <a href="https://parks.qld.gov.au/parks/bowling-green-bay/camping/alligator-falls">
        Alligator Falls camping area, Mount Elliot</a>
      <small>Bowling Green Bay National Park</small>   (the parks listing has the region)
    </h3><p>...</p></li>
"""

import re
from dataclasses import dataclass
from html.parser import HTMLParser

CAMPGROUNDS_A_Z = "https://parks.qld.gov.au/parks/campgrounds-a-z?list=all"
PARKS_A_Z = "https://parks.qld.gov.au/parks/parks-a-z?list=all"
QPWS_FILE = "qpws_pages.json"

CAMPING_URL = re.compile(r"^https://parks\.qld\.gov\.au/parks/[a-z0-9-]+/camping/[a-z0-9-]+$")
PARK_URL = re.compile(r"^https://parks\.qld\.gov\.au/parks/[a-z0-9-]+$")


@dataclass(frozen=True)
class Entry:
    url: str
    name: str
    small: str  # the park, on the camping areas listing; the region, on the parks listing


@dataclass(frozen=True)
class CampingPage:
    url: str
    name: str  # 'Alligator Falls camping area, Mount Elliot'
    park_name: str  # 'Bowling Green Bay National Park'


@dataclass(frozen=True)
class ParkPage:
    url: str
    name: str  # 'Girringun National Park'


class _ListingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.entries: list[Entry] = []
        self._in_entry = False  # inside <li data-park-id>, before its heading ends
        self._in_h3 = False
        self._href: str | None = None
        self._field: str | None = None  # "name" or "small" while inside that element
        self._text = {"name": "", "small": ""}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "li" and "data-park-id" in dict(attrs):
            self._in_entry = True
        elif tag == "h3" and self._in_entry:
            self._in_h3 = True
            self._href = None
            self._text = {"name": "", "small": ""}
        elif self._in_h3 and tag == "a":
            self._href = dict(attrs).get("href")
            self._field = "name"
        elif self._in_h3 and tag == "small":
            self._field = "small"

    def handle_endtag(self, tag: str) -> None:
        if tag in ("a", "small"):
            self._field = None
        elif tag == "h3" and self._in_h3:
            self._in_entry = self._in_h3 = False
            if self._href:
                name, small = (" ".join(self._text[f].split()) for f in ("name", "small"))
                self.entries.append(Entry(self._href.rstrip("/"), name, small))

    def handle_data(self, data: str) -> None:
        if self._field:
            self._text[self._field] += data


def listing(html: str) -> list[Entry]:
    """Every entry in a listing: the link in each <li data-park-id> heading."""
    parser = _ListingParser()
    parser.feed(html)
    return parser.entries


def camping_pages(html: str) -> list[CampingPage]:
    """The camping areas A to Z (/parks/campgrounds-a-z?list=all)."""
    return [CampingPage(e.url, e.name, e.small) for e in listing(html) if CAMPING_URL.match(e.url)]


def park_pages(html: str) -> list[ParkPage]:
    """The parks A to Z (/parks/parks-a-z?list=all)."""
    return [ParkPage(e.url, e.name) for e in listing(html) if PARK_URL.match(e.url)]
