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

// What a typical night there looks like, in plain words: booked sites on nights like these
// against a busy night there (there's no capacity to say how full). At Easter the usual can
// pass the busy night, which is over the whole year: then it says so rather than "51 · 36".
export function usually(c: Pick<QuietCampground, 'typical_sites' | 'busy_night_sites'>): string {
  // Its busy night is the 95th percentile of its open nights: in plain words, hardly ever more.
  if (c.busy_night_sites <= RARELY_BOOKED) {
    return `Hardly ever more than ${sites(Math.max(1, c.busy_night_sites))} booked`
  }
  const busy = Math.round(c.busy_night_sites)
  const typical = Math.round(c.typical_sites)
  const booked = `These nights: usually ${typical === 0 ? 'no sites' : sites(typical)} booked`
  if (typical > busy) return `${booked}, more than on a usual busy night (${busy})`
  if (typical === busy) return `${booked}, as many as on a busy night`
  return `${booked} · ${busy} on a busy night`
}

const percent = (share: number) => `${Math.round(share * 100)}%`

// What a band means, under the toggle: quiet is against the campground's own history.
export function bandNote(band: Band): string {
  const how = {
    quiet: `under ${percent(QUIET_BELOW)} as busy as its own busy nights.`,
    ok: `${percent(QUIET_BELOW).slice(0, -1)}–${percent(BUSY_FROM)} as busy as its own busy nights.`,
    busy: `${percent(BUSY_FROM)} as busy as its own busy nights, or busier.`,
  }[band]
  return `In past years, ${how}`
}

const ORDINAL = new Intl.PluralRules('en-AU', { type: 'ordinal' })
const SUFFIX: Record<string, string> = { one: 'st', two: 'nd', few: 'rd', other: 'th' }

export function ordinal(n: number): string {
  return `${n}${SUFFIX[ORDINAL.select(n)]}`
}

// Where it ranks among all the results for these nights, counted from the nearer end.
export function rankWords(rank: number, of: number): string {
  if (rank === 1) return `The quietest of ${of} for these nights.`
  if (rank === of) return `The busiest of ${of} for these nights.`
  if (rank <= of / 2) return `${ordinal(rank)} quietest of ${of} for these nights.`
  return `${ordinal(of - rank + 1)} busiest of ${of} for these nights.`
}
