import { describe, expect, it } from 'vitest'
import { calendarCell, heatBin, holidayName, niceTicks } from './scales'

describe('heatBin', () => {
  it('puts shares into five equal bins', () => {
    expect([0, 0.19, 0.2, 0.59, 0.6, 0.99].map(heatBin)).toEqual([0, 0, 1, 2, 3, 4])
  })

  it('keeps nights busier than the busiest typical night in the top bin', () => {
    expect(heatBin(1.1)).toBe(4)
  })
})

describe('calendarCell', () => {
  it('starts 2026 on a Thursday, in the first week column', () => {
    expect(calendarCell('2026-01-01')).toEqual({ column: 0, row: 3 })
  })

  it('moves to the next column on Monday', () => {
    expect(calendarCell('2026-01-04')).toEqual({ column: 0, row: 6 }) // Sunday
    expect(calendarCell('2026-01-05')).toEqual({ column: 1, row: 0 }) // Monday
  })

  it('needs a 54th column for a leap year that starts on a Sunday', () => {
    expect(calendarCell('2012-01-01')).toEqual({ column: 0, row: 6 })
    expect(calendarCell('2012-12-31')).toEqual({ column: 53, row: 0 })
  })
})

describe('niceTicks', () => {
  it('rounds up to a clean top tick', () => {
    expect(niceTicks(158)).toEqual([0, 50, 100, 150, 200])
  })

  it('never steps by less than one site', () => {
    expect(niceTicks(3)).toEqual([0, 1, 2, 3])
  })

  it('still draws an axis with no bookings', () => {
    expect(niceTicks(0)).toEqual([0, 1])
  })
})

describe('holidayName', () => {
  it('capitalises the first letter only', () => {
    expect(holidayName("sovereign's birthday")).toBe("Sovereign's birthday")
  })
})
