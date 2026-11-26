from quiet_camps.ingest.qpws import CampingPage, ParkPage, camping_pages, listing, park_pages

# Trimmed from the Internet Archive's captures of the two listings (October 2026).
CAMPING_HTML = """
<nav><a href="https://parks.qld.gov.au/camping/bookings">Bookings and fees</a></nav>
<ul>
<li data-park-id="162357">
   <h3>
        <a href="https://parks.qld.gov.au/parks/bowling-green-bay/camping/alligator-falls">
          Alligator Falls camping area, Mount Elliot</a>

        <small>Bowling Green Bay National Park</small>
    </h3>
    <p>Fit, prepared and experienced walkers can explore grassy open woodlands.</p>
</li><li data-park-id="161609">
   <h3>
        <a href="https://parks.qld.gov.au/parks/rinyirru-lakefield/camping/annie-river/">Annie River
          camping area</a>
        <small>Rinyirru (Lakefield) National Park (CYPAL)</small>
    </h3>
</li><li data-park-id="1">
   <h3><a href="https://parks.qld.gov.au/parks/k-gari/camping/central-station">
     Central Station camping area &amp; K&#8217;gari walkers</a></h3>
</li>
</ul>
"""

PARKS_HTML = """
<h3><a href="https://parks.qld.gov.au/parks/parks-a-z">Parks A to Z listing</a></h3>
<ul>
<li data-park-id="148123">
   <h3>
        <a href="https://parks.qld.gov.au/parks/girringun">Girringun National Park</a>
        <small>Region: Townsville; Tropical North Queensland</small>
    </h3>
    <p>Girringun National Park is comprised of 6 sections.</p>
</li>
</ul>
"""


def test_camping_pages_read_name_and_park() -> None:
    assert camping_pages(CAMPING_HTML) == [
        CampingPage(
            "https://parks.qld.gov.au/parks/bowling-green-bay/camping/alligator-falls",
            "Alligator Falls camping area, Mount Elliot",
            "Bowling Green Bay National Park",
        ),
        CampingPage(
            "https://parks.qld.gov.au/parks/rinyirru-lakefield/camping/annie-river",
            "Annie River camping area",
            "Rinyirru (Lakefield) National Park (CYPAL)",
        ),
        CampingPage(
            "https://parks.qld.gov.au/parks/k-gari/camping/central-station",
            "Central Station camping area & K\u2019gari walkers",
            "",
        ),
    ]


def test_park_pages_read_name() -> None:
    assert park_pages(PARKS_HTML) == [
        ParkPage("https://parks.qld.gov.au/parks/girringun", "Girringun National Park")
    ]


def test_listing_ignores_links_outside_an_entry() -> None:
    # The bookings link in <nav> and "Parks A to Z listing" in a bare <h3> are not entries.
    assert [e.url for e in listing(PARKS_HTML)] == ["https://parks.qld.gov.au/parks/girringun"]
    assert [e.url for e in listing(CAMPING_HTML)] == [
        "https://parks.qld.gov.au/parks/bowling-green-bay/camping/alligator-falls",
        "https://parks.qld.gov.au/parks/rinyirru-lakefield/camping/annie-river",
        "https://parks.qld.gov.au/parks/k-gari/camping/central-station",
    ]
