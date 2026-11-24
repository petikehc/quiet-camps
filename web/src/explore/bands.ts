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

// What a typical night there looks like, in plain words: booked sites on nights like these in
// past years, against its busiest nights (there's no capacity to say how full). At Easter the
// usual can pass the busiest nights, which are over the whole year: then it says so.
export function usually(c: Pick<QuietCampground, 'typical_sites' | 'busy_night_sites'>): string {
  // Its busy night is the 95th percentile of its open nights: in plain words, hardly ever more.
  if (c.busy_night_sites <= RARELY_BOOKED) {
    return `Hardly ever more than ${sites(Math.max(1, c.busy_night_sites))} booked`
  }
  const busy = Math.round(c.busy_night_sites)
  const typical = Math.round(c.typical_sites)
  const booked = `These nights: usually ${typical === 0 ? 'no sites' : sites(typical)} booked in past years`
  if (typical > busy) return `${booked}, more than on its usual busiest nights (${busy}).`
  if (typical === busy) return `${booked}, as many as on its busiest nights.`
  return `${booked}. Its busiest nights: about ${busy}.`
}

const percent = (share: number) => `${Math.round(share * 100)}%`
const BUSIEST = '(its busiest 1 night in 20)' // the 95th percentile, in words

// What a band means, under the toggle: quiet is against the campground's own history.
export function bandNote(band: Band): string {
  const how = {
    quiet: `under ${percent(QUIET_BELOW)} as busy as its busiest nights`,
    ok: `${percent(QUIET_BELOW).slice(0, -1)}–${percent(BUSY_FROM)} as busy as its busiest nights`,
    busy: `${percent(BUSY_FROM)} as busy as its busiest nights or more`,
  }[band]
  return `In past years, ${how} ${BUSIEST}.`
}

const ORDINAL = new Intl.PluralRules('en-AU', { type: 'ordinal' })
const SUFFIX: Record<string, string> = { one: 'st', two: 'nd', few: 'rd', other: 'th' }

export function ordinal(n: number): string {
  return `${n}${SUFFIX[ORDINAL.select(n)]}`
}

// Where it ranks in its band's list for these nights: from the quiet end, or for the busy band
// (listed busiest first) from the busy end, so a quiet card never says "busiest".
export function rankWords(band: Band, rank: number, of: number): string {
  const ones = `${BAND_NAMES[band].toLowerCase()} ones`
  if (of === 1) return `The only ${BAND_NAMES[band].toLowerCase()} one for these nights.`
  const end = band === 'busy' ? 'busiest' : 'quietest'
  return `${rank === 1 ? 'The' : ordinal(rank)} ${end} of ${of} ${ones} for these nights.`
}
