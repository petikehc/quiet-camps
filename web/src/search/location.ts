import type { QuietCampground } from './ResultsTable'

// How sure we are where a campground is, from the location matching in the API's ingest.
// The map draws each kind differently, and the list marks every kind but `exact` with ⚠.
export type Certainty =
  | 'exact' // matched an OpenStreetMap campsite cleanly (or was checked by hand)
  | 'check' // matched one, but something about the match needs a look
  | 'park' // only the park's centre is known
  | 'none' // not on the map at all

const REASONS: Record<string, string> = {
  weak_name: "The map's name only partly matches",
  contains: "One name contains the other, so it may be a different site",
  tie: 'Two equally good matches on the map',
  shared_point: 'Shares its point with another campground',
  edge_of_park: "Just outside its park's boundary",
  no_park_outline: 'No park outline to check the point against',
  rejected_osm: 'A match on the map failed a check',
}

// The OpenStreetMap object a campground was matched to, to check the match against the map.
export function osmLink(c: QuietCampground): { href: string; label: string } | undefined {
  if (c.osm_type === null || c.osm_id === null) return undefined
  const href = `https://www.openstreetmap.org/${c.osm_type}/${c.osm_id}`
  const rejected = c.location_flags.includes('rejected_osm')
  return { href, label: rejected ? 'The rejected match on OpenStreetMap' : 'On OpenStreetMap' }
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
