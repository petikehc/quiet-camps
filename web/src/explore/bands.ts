import type { Band } from './filters'
import type { QuietCampground } from './queries'

// Bands of busyness (typical sites against the campground's own busy nights), set from real
// searches: an ordinary weekend splits 261 / 64 / 24 of 349 campgrounds, Easter 66 / 85 / 241.
export const QUIET_BELOW = 0.25
export const BUSY_FROM = 0.6
// A campground whose busy night is a site or two is rarely booked at all: its % says little.
export const RARELY_BOOKED = 2

export const BAND_NAMES: Record<Band, string> = {
  quiet: 'Quiet',
  ok: 'Not too busy',
  busy: 'Busy',
}

export function bandOf(busyness: number): Band {
  if (busyness < QUIET_BELOW) return 'quiet'
  return busyness < BUSY_FROM ? 'ok' : 'busy'
}

function sites(n: number): string {
  const rounded = Math.round(n)
  return `${rounded} ${rounded === 1 ? 'site' : 'sites'}`
}

// What a typical night there looks like, in plain words: booked sites against its busy nights
// (there's no capacity to say how full).
export function usually(c: Pick<QuietCampground, 'typical_sites' | 'busy_night_sites'>): string {
  // Its busy night is the 95th percentile of its open nights: in plain words, hardly ever more.
  if (c.busy_night_sites <= RARELY_BOOKED) {
    return `Hardly ever more than ${sites(Math.max(1, c.busy_night_sites))} booked`
  }
  const busy = Math.round(c.busy_night_sites)
  const booked = Math.round(c.typical_sites) === 0 ? 'none' : sites(c.typical_sites)
  return `Usually ${booked} booked · ${busy} on its busy nights`
}
