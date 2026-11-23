import { nightDate } from '../charts/dates'
import type { Trips } from './trips'

// Quiet and busy are relative to a campground's own history: a month well under, or over, its
// usual month. Months, so the board changes about every 7 seconds: slow enough to read.
export const QUIET = 0.5 // half its usual month or less
export const BUSIER = 1.25 // a quarter over its usual month or more
export const USUAL_MIN_A_WEEK = 10 // sites: smaller campgrounds are too lumpy to judge
const SHOWN = 3

export type Month = { first: number; last: number } // nights [first, last)

// The calendar months of the trips' year, as ranges of nights.
export function months(trips: Trips): Month[] {
  const found: Month[] = []
  for (let night = 0; night < trips.nights; night++) {
    if (night > 0 && !nightDate(trips.first_night, night).endsWith('-01')) continue
    const previous = found.at(-1)
    if (previous) previous.last = night
    found.push({ first: night, last: trips.nights })
  }
  return found
}

export function monthOf(monthList: Month[], night: number): number {
  return Math.max(0, monthList.findIndex((m) => night >= m.first && night < m.last))
}

// Each campground's sites arriving on an average night of the year.
export function usualNightly(trips: Trips): Float64Array {
  const usual = new Float64Array(trips.campgrounds.length)
  trips.sites.forEach((sites, e) => {
    usual[trips.campground[e]] += sites
  })
  return usual.map((total) => total / trips.nights)
}

export type Count = { campground: number; sites: number; usual: number } // sites in a month

// Each campground's sites arriving in the month, against its usual month: only those that
// usually get enough to judge.
function monthCounts(
  trips: Trips,
  offsets: Uint32Array,
  nightly: Float64Array,
  month: Month,
): Count[] {
  const sites = new Float64Array(trips.campgrounds.length)
  for (let e = offsets[month.first]; e < offsets[month.last]; e++) {
    sites[trips.campground[e]] += trips.sites[e]
  }
  const nights = month.last - month.first
  const usualMin = (USUAL_MIN_A_WEEK / 7) * nights
  return [...sites.keys()]
    .map((c) => ({ campground: c, sites: sites[c], usual: nightly[c] * nights }))
    .filter((count) => count.usual >= usualMin)
}

// Open (someone arrived) and well under its usual month.
function isQuiet({ sites, usual }: Count): boolean {
  return sites > 0 && sites <= QUIET * usual
}

export type MonthBoard = {
  busier: Count[] // most over its usual first
  quiet: Count[] // quietest against its usual first
}

export function monthBoard(
  trips: Trips,
  offsets: Uint32Array,
  nightly: Float64Array,
  month: Month,
): MonthBoard {
  const counts = monthCounts(trips, offsets, nightly, month)
  const rounded = (c: Count): Count => ({
    ...c,
    sites: Math.round(c.sites),
    usual: Math.round(c.usual),
  })
  // Of two as far from their usual, the one usually busier first: it's the bigger story.
  const busier = counts
    .filter((c) => c.sites >= BUSIER * c.usual)
    .sort((a, b) => b.sites / b.usual - a.sites / a.usual || b.usual - a.usual)
  const quiet = counts
    .filter(isQuiet)
    .sort((a, b) => a.sites / a.usual - b.sites / b.usual || b.usual - a.usual)
  return { busier: busier.slice(0, SHOWN).map(rounded), quiet: quiet.slice(0, SHOWN).map(rounded) }
}

// 1 for each campground that's quiet in the month: the map rings these teal.
export function quietMask(
  trips: Trips,
  offsets: Uint32Array,
  nightly: Float64Array,
  month: Month,
): Float32Array {
  const mask = new Float32Array(trips.campgrounds.length)
  for (const c of monthCounts(trips, offsets, nightly, month)) {
    if (isQuiet(c)) mask[c.campground] = 1
  }
  return mask
}
