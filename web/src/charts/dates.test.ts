import { describe, expect, it } from 'vitest'
import { holidayOn, nightDate } from './dates'

describe('holidayOn', () => {
  it('finds the span a night falls in', () => {
    const holidays = [{ name: 'christmas', night: 0, nights: 2 }]
    expect(holidayOn(holidays, 1)?.name).toBe('christmas')
    expect(holidayOn(holidays, 2)).toBeUndefined()
  })
})

describe('nightDate', () => {
  it('counts from the first night, across months and leap days', () => {
    expect(nightDate('2024-01-01', 0)).toBe('2024-01-01')
    expect(nightDate('2024-01-01', 59)).toBe('2024-02-29')
    expect(nightDate('2024-01-01', 365)).toBe('2024-12-31')
  })
})
