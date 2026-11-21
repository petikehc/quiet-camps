import { describe, expect, it } from 'vitest'
import {
  holidayOn,
  nightDate,
  parseTimelapseYear,
  peaks,
  project,
  statewide,
  timelapseYears,
  type Year,
} from './timelapse'

const today = new Date('2026-11-21T10:00:00')

// Two campgrounds, three nights: values row by row.
const year: Year = {
  year: 2025,
  first_night: '2025-01-01',
  nights: 3,
  campgrounds: [
    { id: 3, name: 'Hoop Pines', lat: -28.3, lon: 152.7 },
    { id: 9, name: 'Teewah', lat: null, lon: null },
  ],
  values: [4, 0, 2, 1, 7, 0],
  holidays: [{ name: 'christmas', night: 0, nights: 2 }],
}

describe('parseTimelapseYear', () => {
  it('keeps a year with history', () => {
    expect(parseTimelapseYear({ year: 2011 }, today)).toEqual({ year: 2011 })
    expect(parseTimelapseYear({ year: 2026 }, today)).toEqual({ year: 2026 })
  })

  it.each([undefined, 2010, 2027, 2025.5, '2025'])('falls back to last year for %s', (y) => {
    expect(parseTimelapseYear({ year: y }, today)).toEqual({ year: 2025 })
  })
})

describe('project', () => {
  it('puts north away from the camera and east to the right', () => {
    const [x0, z0] = project(145.8, -19.6)
    const [x1, z1] = project(146.8, -18.6)
    expect([x0, z0]).toEqual([0, -0])
    expect(z1).toBeLessThan(z0)
    expect(x1).toBeCloseTo(Math.cos((19.6 * Math.PI) / 180)) // a degree east is narrower
  })
})

describe('totals', () => {
  it('adds every campground on each night', () => {
    expect(statewide(year)).toEqual([5, 7, 2])
  })

  it("finds each campground's busiest night", () => {
    expect(peaks(year)).toEqual([4, 7])
  })
})

describe('holidayOn', () => {
  it('finds the span a night falls in', () => {
    expect(holidayOn(year.holidays, 1)?.name).toBe('christmas')
    expect(holidayOn(year.holidays, 2)).toBeUndefined()
  })
})

describe('nightDate', () => {
  it('counts from the first night, across months and leap days', () => {
    expect(nightDate('2024-01-01', 0)).toBe('2024-01-01')
    expect(nightDate('2024-01-01', 59)).toBe('2024-02-29')
    expect(nightDate('2024-01-01', 365)).toBe('2024-12-31')
  })
})

describe('timelapseYears', () => {
  it('runs from the first permits to this year', () => {
    const years = timelapseYears(today)
    expect([years[0], years.at(-1), years.length]).toEqual([2011, 2026, 16])
  })
})
