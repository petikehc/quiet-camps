import { describe, expect, it } from 'vitest'
import { bookBy, groupFor, halfBookedWeeks, type LeadTime } from './bookBy'

// Harrys camping area's Easter, from the API: booked 63% two weeks ahead, 39% four weeks ahead.
const easter = [
  { weeks: 0, share: 1 },
  { weeks: 1, share: 0.76 },
  { weeks: 2, share: 0.63 },
  { weeks: 4, share: 0.39 },
  { weeks: 8, share: 0.28 },
  { weeks: 13, share: 0 },
  { weeks: 26, share: 0 },
  { weeks: 52, share: 0 },
]
const lead = (nights: number): LeadTime => ({
  campground_id: 392,
  since: '2023-10-01',
  until: '2026-09-30',
  groups: [{ group: 'easter', nights, booked_by: easter }],
})
const EASTER_2027 = { name: 'easter', night: 0, nights: 4 }

describe('halfBookedWeeks', () => {
  it('finds where half were booked, between the weeks measured', () => {
    expect(halfBookedWeeks(easter)).toBeCloseTo(2 + (0.13 / 0.24) * 2)
  })

  it('is a year when half or more were booked a year ahead', () => {
    expect(halfBookedWeeks([{ weeks: 0, share: 1 }, { weeks: 52, share: 0.6 }])).toBe(52)
  })
})

describe('groupFor', () => {
  it('is the holiday, else a weekend or weeknight', () => {
    expect(groupFor('2027-03-25', EASTER_2027, false)).toBe('easter')
    expect(groupFor('2027-02-12', undefined, false)).toBe('weekend') // a Friday
    expect(groupFor('2027-02-10', undefined, false)).toBe('weeknight') // a Wednesday
  })

  it('is the school holidays for a night in them that is not a public holiday', () => {
    expect(groupFor('2026-12-23', undefined, true)).toBe('school holidays') // a Wednesday
    expect(groupFor('2027-03-25', EASTER_2027, true)).toBe('easter') // the public holiday wins
  })
})

describe('bookBy', () => {
  it('counts back from the arrival', () => {
    expect(bookBy(lead(109), '2027-03-25', EASTER_2027, true)).toEqual({
      group: 'easter',
      weeks: expect.closeTo(3.08, 2) as number,
      date: '2027-03-03',
    })
  })

  it('says nothing from too few booked nights, or a kind of night it has none of', () => {
    expect(bookBy(lead(6), '2027-03-25', EASTER_2027, true)).toBeUndefined()
    expect(bookBy(lead(109), '2027-02-12', undefined, false)).toBeUndefined()
  })
})
