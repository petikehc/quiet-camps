import { describe, expect, it } from 'vitest'
import {
  comingYear,
  holidayFor,
  inSchoolHolidays,
  nightsBetween,
  quietestWeek,
  type AreaYear,
} from './comingYear'

function year(y: number, nights: number, holidays: AreaYear['holidays']): AreaYear {
  return {
    year: y,
    first_night: `${y}-01-01`,
    nights,
    busyness: Array.from({ length: nights }, (_, n) => n / nights),
    open: Array.from({ length: nights }, () => 5),
    holidays,
    school_holidays: y === 2026 ? [{ name: 'summer', night: 344, nights: 21 }] : [],
  }
}

const y2026 = year(2026, 365, [{ name: 'christmas', night: 357, nights: 9 }])
const y2027 = year(2027, 365, [
  { name: 'christmas', night: 0, nights: 2 },
  { name: 'easter', night: 83, nights: 4 },
])

describe('comingYear', () => {
  const coming = comingYear('2026-11-24', [y2026, y2027])

  it('is the 365 nights from today, across the year end', () => {
    expect(coming.values).toHaveLength(365)
    expect(coming.values[0]).toBe(327 / 365) // 24 Nov is night 327 of 2026
    expect(coming.values[38]).toBe(0) // 1 Jan 2027
  })

  it('keeps the school holidays from today', () => {
    expect(coming.schoolHolidays).toEqual([{ name: 'summer', night: 344 - 327, nights: 21 }])
  })

  it('says whether a night is in the school holidays', () => {
    expect(inSchoolHolidays(coming, '2026-12-23')).toBe(true) // the summer holidays' 13th night
    expect(inSchoolHolidays(coming, '2026-12-10')).toBe(false) // the night before they start
  })

  it('counts its holidays from today', () => {
    expect(coming.holidays).toContainEqual({ name: 'easter', night: 38 + 83, nights: 4 })
    expect(holidayFor(coming, '2027-03-26')?.name).toBe('easter')
    expect(holidayFor(coming, '2027-03-30')).toBeUndefined()
  })
})

describe('nightsBetween', () => {
  it('counts calendar days, whatever the clocks do', () => {
    expect(nightsBetween('2026-10-03', '2026-10-05')).toBe(2) // across daylight saving elsewhere
  })
})

describe('quietestWeek', () => {
  it('finds the 7 nights with the lowest mean', () => {
    expect(quietestWeek([5, 5, 1, 1, 1, 1, 1, 1, 1, 5])).toBe(2)
  })

  it('skips weeks with a closed night', () => {
    expect(quietestWeek([0, null, 0, 0, 0, 0, 0, 0, 2, 2])).toBe(2)
    expect(quietestWeek([null, 1, 1])).toBeUndefined()
  })
})
