import { describe, expect, it } from 'vitest'
import { monthBoard, monthOf, months, quietMask, usualNightly } from './quiet'
import { nightOffsets, type Trips } from './trips'

// January to March 2025 (90 nights), each month's arrivals on its first night. A usual March
// (31 nights) for 270 sites in the 90: 93.
const NIGHTS = 90
const FIRSTS = [0, 31, 59] // 1 Jan, 1 Feb, 1 Mar
const MONTHLY: [name: string, jan: number, feb: number, mar: number][] = [
  ['Steady', 90, 90, 90], // as usual
  ['Surge', 30, 30, 210], // over twice its usual March
  ['Lull', 130, 130, 10], // open, at a tenth of its usual March
  ['Shut', 135, 135, 0], // nothing in March: closed, not quiet
  ['Tiny', 10, 10, 1], // a usual March of 7: too small to judge
  ['Closing', 135, 135, 5], // a few arrivals, then closed: under a tenth of its usual
]
const entries = FIRSTS.flatMap((night, m) =>
  MONTHLY.flatMap(([, ...sites], c) => (sites[m] > 0 ? [[night, c, sites[m]] as const] : [])),
)
const perNight = new Array<number>(NIGHTS).fill(0)
for (const [night] of entries) perNight[night]++

const trips: Trips = {
  year: 2025,
  first_night: '2025-01-01',
  nights: NIGHTS,
  origins: [{ postcode: '4000', lat: -27.47, lon: 153.02 }],
  campgrounds: MONTHLY.map(([name], id) => ({ id, name, lat: -27, lon: 153 })),
  per_night: perNight,
  origin: entries.map(() => 0),
  campground: entries.map(([, c]) => c),
  sites: entries.map(([, , s]) => s),
  left_out: { overseas: 0, no_postcode: 0, no_centroid: 0, unlocated: 0 },
  holidays: [],
}
const offsets = nightOffsets(trips.per_night)
const nightly = usualNightly(trips)
const named = (list: { campground: number }[]) => list.map((c) => MONTHLY[c.campground][0])

describe('months', () => {
  it('splits the year at each first of the month', () => {
    const found = months(trips)
    expect(found).toEqual([
      { first: 0, last: 31 },
      { first: 31, last: 59 },
      { first: 59, last: 90 },
    ])
    expect(monthOf(found, 60)).toBe(2)
  })
})

describe('monthBoard', () => {
  const march = months(trips)[2]
  const board = monthBoard(trips, offsets, nightly, march)

  it('finds who is busier than their usual month', () => {
    expect(board.busier).toEqual([{ campground: 1, sites: 210, usual: 93 }])
  })

  it('finds who is at half their usual month or less', () => {
    expect(board.quiet).toEqual([{ campground: 2, sites: 10, usual: 93 }])
  })

  it('never calls a closed campground (none arriving) or a tiny one quiet', () => {
    expect(named(board.quiet)).not.toContain('Shut')
    expect(named(board.quiet)).not.toContain('Closing') // closed for most of the month
    expect(named([...board.quiet, ...board.busier])).not.toContain('Tiny')
  })

  it('puts the usually busier of two as quiet first', () => {
    // Steady and Surge both at a quarter of these usual months: 90 of 360, 210 of 840.
    const tie = monthBoard(trips, offsets, new Float64Array([360 / 31, 840 / 31, 3, 3, 0, 3]), march)
    expect(named(tie.quiet)).toEqual(['Lull', 'Surge', 'Steady']) // Lull at a tenth first
  })
})

describe('quietMask', () => {
  it('marks the quiet ones for the map', () => {
    expect([...quietMask(trips, offsets, nightly, months(trips)[2])]).toEqual([0, 0, 1, 0, 0, 0])
  })
})
