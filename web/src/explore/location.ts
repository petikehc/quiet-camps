import type { QuietCampground } from './queries'

// How sure we are where a campground is, from the location matching in the API's ingest.
// Campers see two kinds of dot: the campground's own spot, or its park's centre. The review
// view (?review=locations) also shows the matches that need a check, with the reasons.
export type Certainty =
  | 'exact' // matched an OpenStreetMap campsite cleanly (or was checked by hand)
  | 'check' // matched one, but something about the match needs a look
  | 'park' // only the park's centre is known
  | 'none' // not on the map at all

const REASONS: Record<string, string> = {
  weak_name: "The map's name only partly matches",
  contains: 'One name contains the other, so it may be a different site',
  tie: 'Two equally good matches on the map',
  shared_point: 'Shares its point with another campground',
  edge_of_park: "Just outside its park's boundary",
  no_park_outline: 'No park outline to check the point against',
  rejected_osm: 'A match on the map failed a check',
}

export function locationNote(c: QuietCampground): { certainty: Certainty; reasons: string[] } {
  // `reviewed` means someone checked it by hand: a reason to trust it, not to look again.
  const reasons = c.location_flags.filter((f) => f !== 'reviewed').map((f) => REASONS[f] ?? f)
  if (c.lat === null || c.lon === null) {
    return { certainty: 'none', reasons: ['Not on the map: no location found', ...reasons] }
  }
  if (c.location_source === 'park_osm' || c.location_source === 'park_qld') {
    return { certainty: 'park', reasons: ['Shown at the middle of its park', ...reasons] }
  }
  return { certainty: reasons.length > 0 ? 'check' : 'exact', reasons }
}

// What the map and the list show: for campers a flagged match is still the campground's spot,
// and only the review view tells them apart.
export function shownLocation(
  c: QuietCampground,
  review: boolean,
): { certainty: Certainty; notes: string[] } {
  const { certainty, reasons } = locationNote(c)
  if (review) return { certainty, notes: reasons }
  if (certainty === 'none') return { certainty, notes: ['Not on the map: no location found'] }
  if (certainty === 'park') {
    return { certainty, notes: [`Exact spot unknown: shown in the middle of ${c.park_name}`] }
  }
  return { certainty: 'exact', notes: [] }
}

// The OpenStreetMap object a campground was matched to. A rejected match is only worth
// showing to someone reviewing the matching; to a camper it would be a link to the wrong place.
export function osmLink(
  c: QuietCampground,
  review: boolean,
): { href: string; label: string } | undefined {
  if (c.osm_type === null || c.osm_id === null) return undefined
  const href = `https://www.openstreetmap.org/${c.osm_type}/${c.osm_id}`
  if (!c.location_flags.includes('rejected_osm')) return { href, label: 'On OpenStreetMap' }
  return review ? { href, label: 'The rejected match on OpenStreetMap' } : undefined
}

// The campground's page on parks.qld.gov.au, as the API matched it: its camping area's page, or
// its park's. Without either, QPWS's park finder with the park's name.
export function qpwsLink(c: QuietCampground): { href: string; label: string } {
  if (c.qpws_url !== null && c.qpws_url_kind === 'camping') {
    return { href: c.qpws_url, label: 'Camping area on QPWS' }
  }
  if (c.qpws_url !== null) return { href: c.qpws_url, label: 'Park on QPWS' }
  const finder = new URLSearchParams({ type: 'park', names: c.park_name })
  return { href: `https://parks.qld.gov.au/parks?${finder}`, label: 'Find the park on QPWS' }
}
