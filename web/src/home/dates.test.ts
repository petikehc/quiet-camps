import { describe, expect, it } from 'vitest'
import { isTrip, sameNight, tripLabel } from './dates'

describe('sameNight', () => {
  it("finds the night with the same day and month in the map's year", () => {
    expect(sameNight('2026-01-01', 2025)).toBe(0)
    expect(sameNight('2027-04-18', 2025)).toBe(107)
    expect(sameNight('2026-12-31', 2025)).toBe(364)
  })

  it('puts 29 February on the 28th in a year without one', () => {
    expect(sameNight('2028-02-29', 2025)).toBe(58)
    expect(sameNight('2028-02-29', 2024)).toBe(59)
  })
})

describe('isTrip', () => {
  it('needs both dates, leaving after arriving', () => {
    expect(isTrip('2026-04-18', '2026-04-21')).toBe(true)
    expect(isTrip('2026-04-18', '')).toBe(false)
    expect(isTrip('', '2026-04-21')).toBe(false)
  })

  it('is not a trip when you leave on or before the day you arrive', () => {
    expect(isTrip('2026-04-18', '2026-04-18')).toBe(false)
    expect(isTrip('2026-04-18', '2026-04-17')).toBe(false)
  })
})

describe('tripLabel', () => {
  it('says the month once within a month', () => {
    expect(tripLabel('2026-04-18', '2026-04-21')).toBe('18–21 Apr')
  })

  it('names both months across a month', () => {
    expect(tripLabel('2026-04-30', '2026-05-03')).toBe('30 Apr – 3 May')
  })
})
