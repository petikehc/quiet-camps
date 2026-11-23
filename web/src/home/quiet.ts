import type { Trips } from './trips'

// Quiet is relative to a campground's own history: a week well under its usual. Arrivals are
// counted in calendar weeks of 7 nights, so the board changes once a week, not every frame.
export const WEEK = 7
export const QUIET = 0.5 // half its usual week or less
export const USUAL_MIN = 10 // sites a week: smaller campgrounds are too lumpy to call quiet
const SHOWN = 3

// Whole weeks in the year; the last night or two belong to the last week.
export function weeks(nights: number): number {
  return Math.max(1, Math.floor(nights / WEEK))
}

export function weekOf(night: number, nights: number): number {
  return Math.min(Math.floor(night / WEEK), weeks(nights) - 1)
}

// Each campground's sites arriving in an average week of the year.
export function usualWeekly(trips: Trips): Float64Array {
  const usual = new Float64Array(trips.campgrounds.length)
  trips.sites.forEach((sites, e) => {
    usual[trips.campground[e]] += sites
  })
  const perWeek = WEEK / trips.nights
  return usual.map((total) => total * perWeek)
}

// Sites arriving at each campground in week `w`, scaled to 7 nights for the longer last week.
function weekSites(trips: Trips, offsets: Uint32Array, w: number): Float64Array {
  const first = w * WEEK
  const last = w === weeks(trips.nights) - 1 ? trips.nights : first + WEEK
  const sites = new Float64Array(trips.campgrounds.length)
  for (let e = offsets[first]; e < offsets[last]; e++) sites[trips.campground[e]] += trips.sites[e]
  const scale = WEEK / (last - first)
  return scale === 1 ? sites : sites.map((s) => s * scale)
}

// Open (someone arrived), usually busy enough to judge, and well under its usual.
function isQuiet(sites: number, usual: number): boolean {
  return sites > 0 && usual >= USUAL_MIN && sites <= QUIET * usual
}

export type WeekBoard = {
  busy: { campground: number; sites: number }[] // busiest first
  quiet: { campground: number; sites: number; usual: number }[] // quietest first
}

export function weekBoard(trips: Trips, offsets: Uint32Array, usual: Float64Array, w: number): WeekBoard {
  const sites = weekSites(trips, offsets, w)
  const all = [...sites.keys()]
  const busy = all
    .filter((c) => sites[c] > 0)
    .sort((a, b) => sites[b] - sites[a] || a - b)
    .slice(0, SHOWN)
    .map((campground) => ({ campground, sites: Math.round(sites[campground]) }))
  const quiet = all
    .filter((c) => isQuiet(sites[c], usual[c]))
    .sort((a, b) => sites[a] / usual[a] - sites[b] / usual[b] || usual[b] - usual[a])
    .slice(0, SHOWN)
    .map((campground) => ({
      campground,
      sites: Math.round(sites[campground]),
      usual: Math.round(usual[campground]),
    }))
  return { busy, quiet }
}

// 1 for each campground that's quiet in week `w`: the map lights these teal.
export function quietMask(trips: Trips, offsets: Uint32Array, usual: Float64Array, w: number): Float32Array {
  const sites = weekSites(trips, offsets, w)
  return Float32Array.from(sites, (s, c) => (isQuiet(s, usual[c]) ? 1 : 0))
}
