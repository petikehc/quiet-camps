import { describe, expect, it } from 'vitest'
import { locationNote, osmLink, shownLocation } from './location'
import type { QuietCampground } from './queries'

const camp = (overrides: Partial<QuietCampground>): QuietCampground => ({
  id: 1,
  name: 'Fern Flat',
  park_name: 'Mackay Highlands Great Walk',
  busyness: 0.1,
  typical_sites: 2,
  history: 10,
  busy_night_sites: 6,
  lat: -21.1,
  lon: 148.5,
  location_source: 'osm',
  location_flags: [],
  osm_type: null,
  osm_id: null,
  distance_km: null,
  ...overrides,
})

const rejected = camp({
  location_source: 'park_qld',
  location_flags: ['rejected_osm'],
  osm_type: 'way',
  osm_id: 1,
})

describe('osmLink', () => {
  it('links to the matched OpenStreetMap object, for everyone', () => {
    const matched = camp({ osm_type: 'node', osm_id: 6839356357 })
    const link = { href: 'https://www.openstreetmap.org/node/6839356357', label: 'On OpenStreetMap' }
    expect(osmLink(matched, false)).toEqual(link)
    expect(osmLink(matched, true)).toEqual(link)
  })

  it('shows a rejected match only to a reviewer, and says it was rejected', () => {
    expect(osmLink(rejected, false)).toBeUndefined()
    expect(osmLink(rejected, true)?.label).toBe('The rejected match on OpenStreetMap')
  })

  it('has no link without a match', () => {
    expect(osmLink(camp({}), true)).toBeUndefined()
  })
})

describe('shownLocation', () => {
  const flagged = camp({ location_flags: ['shared_point'] })

  it('shows campers a flagged match as the campground’s own spot, with no notes', () => {
    expect(shownLocation(flagged, false)).toEqual({ certainty: 'exact', notes: [] })
  })

  it('shows a reviewer the flagged match and why', () => {
    expect(shownLocation(flagged, true)).toEqual({
      certainty: 'check',
      notes: ['Shares its point with another campground'],
    })
  })

  it('tells campers in plain words when only the park is known', () => {
    expect(shownLocation(rejected, false)).toEqual({
      certainty: 'park',
      notes: ['Exact spot unknown: shown in the middle of Mackay Highlands Great Walk'],
    })
  })

  it('keeps every reason for a reviewer of a park-centre point', () => {
    expect(shownLocation(rejected, true).notes).toEqual([
      'Shown at the middle of its park',
      'A match on the map failed a check',
    ])
  })

  it('says when a campground is not on the map', () => {
    const lost = camp({ lat: null, lon: null, location_source: null })
    expect(shownLocation(lost, false)).toEqual({
      certainty: 'none',
      notes: ['Not on the map: no location found'],
    })
  })
})

describe('locationNote', () => {
  it('trusts a clean OpenStreetMap match', () => {
    expect(locationNote(camp({}))).toEqual({ certainty: 'exact', reasons: [] })
  })

  it('trusts a match checked by hand', () => {
    expect(locationNote(camp({ location_flags: ['reviewed'] })).certainty).toBe('exact')
    expect(locationNote(camp({ location_source: 'manual', location_flags: ['reviewed'] })).certainty).toBe('exact')
  })

  it('asks for a check, with the reasons, when a match is flagged', () => {
    const note = locationNote(camp({ location_flags: ['shared_point', 'reviewed', 'edge_of_park'] }))
    expect(note).toEqual({
      certainty: 'check',
      reasons: ['Shares its point with another campground', "Just outside its park's boundary"],
    })
  })

  it('says when only the park is known', () => {
    for (const location_source of ['park_osm', 'park_qld']) {
      expect(locationNote(camp({ location_source })).certainty).toBe('park')
    }
  })

  it('keeps the reason a park-centre point lost its own match', () => {
    const note = locationNote(camp({ location_source: 'park_qld', location_flags: ['rejected_osm'] }))
    expect(note.reasons).toEqual(['Shown at the middle of its park', 'A match on the map failed a check'])
  })

  it('leaves campgrounds without coordinates off the map', () => {
    const note = locationNote(camp({ lat: null, lon: null, location_source: null }))
    expect(note.certainty).toBe('none')
  })

  it('shows an unknown flag as is, rather than hiding it', () => {
    expect(locationNote(camp({ location_flags: ['new_flag'] })).reasons).toEqual(['new_flag'])
  })
})
