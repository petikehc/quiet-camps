import type { components } from '../api/schema'
import { projection } from '../projection'

export type Trips = components['schemas']['TripsOut']

export const DAY = 0.25 // seconds of animation per night: a year in about 90 seconds
export const TRAIL = 0.35 // a trail's tail, as a share of its flight
// Australia's middle, so the continent keeps its shape.
export const project = projection({ lon: 134, lat: -28 })

// When the trips are, in words: "in 2025", or for the latest 12 months, "in the 12 months to
// September 2026".
export function periodWords(trips: Pick<Trips, 'year' | 'first_night' | 'nights'>): string {
  if (trips.year !== null) return `in ${trips.year}`
  const [year, month, day] = trips.first_night.split('-').map(Number)
  const last = new Date(Date.UTC(year, month - 1, day + trips.nights - 1))
  return `in the 12 months to ${last.toLocaleDateString('en-AU', { month: 'long', year: 'numeric', timeZone: 'UTC' })}`
}

// A night's entries run from offsets[night] to offsets[night + 1]: the API sends how many
// entries each night has instead of a night per entry.
export function nightOffsets(perNight: number[]): Uint32Array {
  const offsets = new Uint32Array(perNight.length + 1)
  perNight.forEach((count, night) => {
    offsets[night + 1] = offsets[night] + count
  })
  return offsets
}

// Where in its night an entry lands, from 0 to 1: a hash of its index, not Math.random, so
// arrivals spread through the night the same way every loop instead of pulsing together.
export function jitter(entry: number): number {
  let x = Math.imul(entry ^ 0x9e3779b9, 0x85ebca6b)
  x ^= x >>> 13
  x = Math.imul(x, 0xc2b2ae35)
  x ^= x >>> 16
  return (x >>> 0) / 2 ** 32
}

// Seconds in the air for a trip this long (in degrees of latitude): a short hop to the coast
// still reads as a trip, and a trip across the country doesn't take all week.
export function flightSeconds(distance: number): number {
  return 0.6 + 0.35 * Math.sqrt(distance)
}
const LONGEST_FLIGHT = flightSeconds(45) // corner to corner

// How bright a trail is at t (0 at home, 1 at the campground), `since` seconds after it left:
// 1 at the head, fading to 0 at the end of its tail, and 0 where there's no trail. After
// landing, the tail drains into the campground. The vertex shader does the same sum.
export function trailAlpha(since: number, duration: number, t: number): number {
  const behind = since / duration - t
  if (behind < 0 || behind > TRAIL) return 0
  return 1 - behind / TRAIL
}

// Nights either side of tonight whose arrivals can be in the air tonight: leaving up to a
// longest flight before they land, their tails gone a share of it after.
const AHEAD = Math.ceil(LONGEST_FLIGHT / DAY) + 1
const BEHIND = Math.ceil((LONGEST_FLIGHT * TRAIL) / DAY) + 1

export type Range = { from: number; to: number; shift: number } // entries [from, to)

// The entries that can be drawn during `night`, as ranges of entries. The loop has no seam:
// near the year's end the window reaches into next loop's January (shift +1 loop, in
// seconds), and early in January back into last loop's December (shift -1 loop).
export function inFlight(offsets: Uint32Array, night: number): Range[] {
  const nights = offsets.length - 1
  const loop = nights * DAY
  const ranges: Range[] = []
  for (let n = night - BEHIND; n <= night + AHEAD; n++) {
    const wrapped = ((n % nights) + nights) % nights
    const shift = Math.floor(n / nights) * loop
    const [from, to] = [offsets[wrapped], offsets[wrapped + 1]]
    const last = ranges.at(-1)
    if (last && last.to === from && last.shift === shift) last.to = to
    else if (to > from) ranges.push({ from, to, shift })
  }
  return ranges
}

// The most entries any night's window holds: the size of the GPU buffers.
export function mostInFlight(offsets: Uint32Array): number {
  let most = 0
  for (let night = 0; night < offsets.length - 1; night++) {
    most = Math.max(most, size(inFlight(offsets, night)))
  }
  return most
}

export function size(ranges: Range[]): number {
  return ranges.reduce((sum, r) => sum + r.to - r.from, 0)
}

export function sitesOn(trips: Trips, offsets: Uint32Array, night: number): number {
  let sites = 0
  for (let e = offsets[night]; e < offsets[night + 1]; e++) sites += trips.sites[e]
  return sites
}

// Sites arriving each night, every campground together: the year strip's shape.
export function nightlySites(trips: Trips, offsets: Uint32Array): number[] {
  return Array.from({ length: trips.nights }, (_, night) => sitesOn(trips, offsets, night))
}

// The night with the most arrivals: the still shown when motion is reduced.
export function busiestNight(trips: Trips, offsets: Uint32Array): number {
  let best = 0
  for (let n = 1; n < trips.nights; n++) {
    if (sitesOn(trips, offsets, n) > sitesOn(trips, offsets, best)) best = n
  }
  return best
}
