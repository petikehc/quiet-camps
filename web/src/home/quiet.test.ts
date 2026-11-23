import { describe, expect, it } from 'vitest'
import { quietMask, usualWeekly, weekBoard, weekOf, weeks } from './quiet'
import { nightOffsets, type Trips } from './trips'

// Five campgrounds over 3 weeks (21 nights). Their usual weeks: Busy 40, Steady 20, Lull 20,
// Shut 20 and Tiny 4 sites. Week 2 is the one that's looked at.
const NIGHTS = 21
const entries: [night: number, campground: number, sites: number][] = [
  [0, 0, 40], [8, 0, 40], [14, 0, 40], // Busy: as usual every week
  [0, 1, 20], [8, 1, 20], [14, 1, 20], // Steady: as usual
  [0, 2, 30], [8, 2, 28], [15, 2, 2], // Lull: open, but a tenth of its usual
  [0, 3, 30], [8, 3, 30], // Shut: nothing in week 2, so closed, not quiet
  [0, 4, 6], [8, 4, 5], [15, 4, 1], // Tiny: a quarter of its usual, but too small to call quiet
]
entries.sort((a, b) => a[0] - b[0])
const perNight = new Array<number>(NIGHTS).fill(0)
for (const [night] of entries) perNight[night]++

const trips: Trips = {
  year: 2025,
  first_night: '2025-01-01',
  nights: NIGHTS,
  origins: [{ postcode: '4000', lat: -27.47, lon: 153.02 }],
  campgrounds: ['Busy', 'Steady', 'Lull', 'Shut', 'Tiny'].map((name, id) => ({ id, name, lat: -27, lon: 153 })),
  per_night: perNight,
  origin: entries.map(() => 0),
  campground: entries.map(([, c]) => c),
  sites: entries.map(([, , s]) => s),
  left_out: { overseas: 0, no_postcode: 0, no_centroid: 0, unlocated: 0 },
  holidays: [],
}
const offsets = nightOffsets(trips.per_night)
const usual = usualWeekly(trips)

describe('weekOf', () => {
  it('counts weeks of 7 nights from the first night', () => {
    expect([0, 6, 7, 20].map((n) => weekOf(n, 21))).toEqual([0, 0, 1, 2])
  })

  it("folds the year's last night or two into its last week", () => {
    expect(weeks(365)).toBe(52)
    expect(weekOf(364, 365)).toBe(51)
  })
})

describe('usualWeekly', () => {
  it("is each campground's sites a week, on average over the year", () => {
    expect([...usual]).toEqual([40, 20, 20, 20, 4])
  })
})

describe('weekBoard', () => {
  const board = weekBoard(trips, offsets, usual, 2)

  it('ranks the busiest campgrounds by sites arriving that week', () => {
    expect(board.busy.map((b) => [trips.campgrounds[b.campground].name, b.sites])).toEqual([
      ['Busy', 40],
      ['Steady', 20],
      ['Lull', 2],
    ])
  })

  it('finds campgrounds at half their own usual week or less', () => {
    expect(board.quiet.map((q) => [trips.campgrounds[q.campground].name, q.sites, q.usual])).toEqual([
      ['Lull', 2, 20],
    ])
  })

  it('never calls a closed campground (none arriving) or a tiny one quiet', () => {
    const names = board.quiet.map((q) => trips.campgrounds[q.campground].name)
    expect(names).not.toContain('Shut')
    expect(names).not.toContain('Tiny')
  })

  it('puts the quietest first, and of two as quiet, the one usually busier', () => {
    // Busy and Steady both at a quarter of these usual weeks; Lull at a tenth.
    const tie = weekBoard(trips, offsets, new Float64Array([160, 80, 20, 20, 4]), 2)
    expect(tie.quiet.map((q) => q.campground)).toEqual([2, 0, 1])
  })
})

describe('quietMask', () => {
  it('marks open campgrounds at half their usual week or less', () => {
    expect([...quietMask(trips, offsets, usual, 2)]).toEqual([0, 0, 1, 0, 0])
  })
})
