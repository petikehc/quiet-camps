# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **People planning a camping trip in a Queensland national park**, from Queensland or interstate, who would rather not camp beside a crowd. They have dates (often a long weekend or the school holidays) and want to know where is usually quiet on them.
- **The curious**: people who like seeing a place through its data, and come for the story of how Queensland camps (where people travel from, when the crowds arrive, which campgrounds fill and which stay empty).

## Product Purpose

A creative reading of Queensland's public camping-permit data, from 2011 to now. The site shows how Queensland camps: trips from home postcodes to campgrounds, the year's rhythm of holidays and peaks, and each campground's own history. Finding a campground that is usually quiet on your dates is one feature among these, and the most practical one.

Success: a visitor understands something true about Queensland camping that they didn't before, and a camper leaves with a campground that is likely to be quiet on their dates.

## Positioning

Built on every QPWS camping permit since 2011, not on reviews or guesses. "Quiet" means quiet compared with that campground's own history, which no booking site shows.

## Operating Context

- Bookings for Queensland national park campgrounds are made through QPWS. This site doesn't take bookings; it sends campers there informed.
- Peaks follow public holidays and their long weekends, Easter, Christmas and the school holidays.

## Capabilities and Constraints

- Pages: the homepage (the latest 12 months of trips from home postcodes to campgrounds, and one plain-words question), the explorer ("the map") (a full-screen map of the campgrounds that are usually quiet, not too busy or busy on your dates, near a place if you like; the coming year to pick dates from; when people book) and campground pages (calendar, years, lead time).
- The data is **past bookings, not live availability**. Never imply a campground is free.
- The permits have no campsite capacity and no coordinates: quiet is relative to each campground's own history; locations come from OpenStreetMap and park outlines.
- A "trip" is a stay under one booking; counts are campsites (sites booked), not people or bookings.
- Some trips can't be drawn: from overseas, with no postcode, or a PO-box postcode.
- The name is "Quiet Camps" for now. A rename is undecided.

## Brand Commitments

- Not affiliated with or endorsed by Queensland Parks and Wildlife Service or the Queensland Government, and must never look like it.
- Attribution stays visible: camping permits © State of Queensland (CC BY 4.0); locations © OpenStreetMap contributors (ODbL); boundaries and postal areas © Commonwealth of Australia, ABS (CC BY 4.0). The homepage's night sounds are public-domain (CC0) recordings from Freesound, credited in `web/public/sounds/CREDITS.md`.
- Sound is never automatic: night sounds are off on every visit until switched on.
- Voice: plain Australian English, specific and honest about what the data can and can't say.

## Brand Feeling

**"I know something the crowd doesn't."** A visitor should feel let in on a local's secret, not handed a booking tool. In order: wonder (every trail piling onto the same coast), a quiet smirk (everyone does the same thing), being let in (these places are empty, and could be yours), then calm confidence (real data, said plainly). They leave feeling smart and unhurried, already picturing a campfire with no generator next door.

- **A mate who's camped everywhere**, not a brand: short, dry, Australian, warm.
- **Cheeky, never snarky.** Tease the crowd and never sneer at it: the reader is usually part of it.
- **Calm is the reward.** Words like quiet, room, space, still. No "hidden gems", "secret spots" or "off the beaten track".
- **Honest every time.** "Usually", "past bookings": the confidence comes from the data, not from hype.
- The headline: "The map you need to beat the crowd." An empty result says what to try next ("Try a week later?"), never just "No results".

## Evidence on Hand

- The permit data itself (2011 onwards) and everything derived from it: real campgrounds, real counts, real dates.
- No testimonials, user numbers, reviews or press. Don't invent any.

## Product Principles

1. The data is the imagery: show real trips and real counts, not stock photos or decoration.
2. Honest numbers: say what is counted (campsites, not people), and what is left out.
3. Quiet is relative: always compared with a campground's own history.
4. Insight first, tool second: the story earns the visit; the map turns it into a trip.

## Accessibility & Inclusion

- Respect reduced motion: no autoplay, a still frame instead.
- Anything shown only as animation or a chart is also given in words for screen readers.
- Text and chart colours meet WCAG AA contrast in light and dark themes.
