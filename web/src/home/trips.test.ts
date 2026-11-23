import { describe, expect, it } from 'vitest'
import {
  busiestNight,
  DAY,
  flightSeconds,
  homeYear,
  inFlight,
  jitter,
  mostInFlight,
  nightOffsets,
  sitesOn,
  size,
  trailAlpha,
  TRAIL,
  type Trips,
} from './trips'

// Four nights: two entries, none, one, three.
const trips: Trips = {
  year: 2025,
  first_night: '2025-01-01',
  nights: 4,
  origins: [
    { postcode: '4000', lat: -27.47, lon: 153.02 },
    { postcode: '2000', lat: -33.87, lon: 151.21 },
  ],
  campgrounds: [
    { id: 3, name: 'Hoop Pines', lat: -28.3, lon: 152.7 },
    { id: 9, name: 'Teewah', lat: -26.2, lon: 153.1 },
  ],
  per_night: [2, 0, 1, 3],
  origin: [0, 1, 0, 0, 1, 0],
  campground: [1, 0, 1, 1, 1, 0],
  sites: [2, 1, 4, 1, 3, 1],
  left_out: { overseas: 0, no_postcode: 0, no_centroid: 0, unlocated: 0 },
  holidays: [],
}
const offsets = nightOffsets(trips.per_night)

describe('nightOffsets', () => {
  it("finds each night's entries", () => {
    expect([...offsets]).toEqual([0, 2, 2, 3, 6])
    expect(sitesOn(trips, offsets, 3)).toBe(5)
    expect(sitesOn(trips, offsets, 1)).toBe(0)
  })
})

describe('jitter', () => {
  it('is the same every time, between 0 and 1, and spread out', () => {
    const values = Array.from({ length: 1000 }, (_, i) => jitter(i))
    expect(values.map((_, i) => jitter(i))).toEqual(values)
    expect(Math.min(...values)).toBeGreaterThanOrEqual(0)
    expect(Math.max(...values)).toBeLessThan(1)
    expect(values.filter((v) => v < 0.5).length).toBeGreaterThan(450)
    expect(values.filter((v) => v < 0.5).length).toBeLessThan(550)
  })
})

describe('trailAlpha', () => {
  const flight = flightSeconds(4) // 1.3 s

  it('has no trail before it leaves', () => {
    expect(trailAlpha(-0.1, flight, 0)).toBe(0)
  })

  it('is brightest at the head and fades along its tail', () => {
    const since = flight / 2 // the head is halfway
    expect(trailAlpha(since, flight, 0.5)).toBe(1)
    expect(trailAlpha(since, flight, 0.5 - TRAIL / 2)).toBeCloseTo(0.5)
    expect(trailAlpha(since, flight, 0.5 - TRAIL - 0.01)).toBe(0)
    expect(trailAlpha(since, flight, 0.6)).toBe(0) // ahead of the head
  })

  it('drains into the campground after landing, then is gone', () => {
    expect(trailAlpha(flight * (1 + TRAIL / 2), flight, 1)).toBeCloseTo(0.5)
    expect(trailAlpha(flight * (1 + TRAIL + 0.01), flight, 1)).toBe(0)
  })

  it('flies longer trips for longer', () => {
    expect(flightSeconds(30)).toBeGreaterThan(flightSeconds(1))
  })
})

describe('inFlight', () => {
  // 40 nights of one entry each: long enough that a window doesn't wrap onto itself.
  const long = nightOffsets(new Array<number>(40).fill(1))
  const loop = 40 * DAY

  it('takes the nights around tonight, no shift mid-year', () => {
    const [range, ...rest] = inFlight(long, 20)
    expect(rest).toEqual([])
    expect(range.shift).toBe(0)
    expect(range.from).toBeLessThan(20)
    expect(range.to).toBeGreaterThan(21)
  })

  it("reaches into next loop's January at the year's end", () => {
    const ranges = inFlight(long, 39)
    expect(ranges[0]).toMatchObject({ to: 40, shift: 0 })
    expect(ranges[1]).toMatchObject({ from: 0, shift: loop })
  })

  it("reaches back into last loop's December on New Year's Day", () => {
    const ranges = inFlight(long, 0)
    expect(ranges[0]).toMatchObject({ to: 40, shift: -loop })
    expect(ranges[1]).toMatchObject({ from: 0, shift: 0 })
  })

  it('sizes the buffers for the fullest window', () => {
    expect(mostInFlight(long)).toBe(size(inFlight(long, 20)))
  })
})

describe('busiestNight', () => {
  it('finds the night with the most sites arriving', () => {
    expect(busiestNight(trips, offsets)).toBe(3)
  })
})

describe('homeYear', () => {
  it('is last year', () => {
    expect(homeYear(new Date('2026-11-22T10:00:00'))).toBe(2025)
  })
})
