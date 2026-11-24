import { describe, expect, it } from 'vitest'
import { bandNote, bandOf, ordinal, rankWords, usually } from './bands'

describe('bandOf', () => {
  it('splits busyness at a quarter and 60%', () => {
    expect([0, 0.24, 0.25, 0.59, 0.6, 1.3].map(bandOf)).toEqual([
      'quiet',
      'quiet',
      'ok',
      'ok',
      'busy',
      'busy',
    ])
  })
})

describe('usually', () => {
  it('says booked sites on these nights against a busy night', () => {
    expect(usually({ typical_sites: 2.4, busy_night_sites: 40 })).toBe(
      'These nights: usually 2 sites booked · 40 on a busy night',
    )
    expect(usually({ typical_sites: 1, busy_night_sites: 7 })).toBe(
      'These nights: usually 1 site booked · 7 on a busy night',
    )
  })

  it('says no sites, not none, when a typical night has nothing booked', () => {
    expect(usually({ typical_sites: 0.2, busy_night_sites: 26 })).toBe(
      'These nights: usually no sites booked · 26 on a busy night',
    )
  })

  it("says when these nights are busier than its usual busy night, so usual isn't over busy", () => {
    expect(usually({ typical_sites: 51, busy_night_sites: 36 })).toBe(
      'These nights: usually 51 sites booked, more than on a usual busy night (36)',
    )
    expect(usually({ typical_sites: 36.2, busy_night_sites: 36 })).toBe(
      'These nights: usually 36 sites booked, as many as on a busy night',
    )
  })

  it('says a campground whose busy nights have a site or two hardly ever has more', () => {
    expect(usually({ typical_sites: 0, busy_night_sites: 0 })).toBe(
      'Hardly ever more than 1 site booked',
    )
    expect(usually({ typical_sites: 1, busy_night_sites: 2 })).toBe(
      'Hardly ever more than 2 sites booked',
    )
  })
})

describe('bandNote', () => {
  it('says what each band means, from its thresholds', () => {
    expect(bandNote('quiet')).toBe('In past years, under 25% as busy as its own busy nights.')
    expect(bandNote('ok')).toBe('In past years, 25–60% as busy as its own busy nights.')
    expect(bandNote('busy')).toBe('In past years, 60% as busy as its own busy nights, or busier.')
  })
})

describe('ordinal', () => {
  it('says 1st, 2nd, 3rd, 11th, 12th, 13th, 21st, 22nd, 37th', () => {
    expect([1, 2, 3, 4, 11, 12, 13, 21, 22, 37, 101].map(ordinal)).toEqual([
      '1st',
      '2nd',
      '3rd',
      '4th',
      '11th',
      '12th',
      '13th',
      '21st',
      '22nd',
      '37th',
      '101st',
    ])
  })
})

describe('rankWords', () => {
  it('counts from the nearer end', () => {
    expect(rankWords(1, 38)).toBe('The quietest of 38 for these nights.')
    expect(rankWords(3, 38)).toBe('3rd quietest of 38 for these nights.')
    expect(rankWords(19, 38)).toBe('19th quietest of 38 for these nights.')
    expect(rankWords(36, 38)).toBe('3rd busiest of 38 for these nights.')
    expect(rankWords(38, 38)).toBe('The busiest of 38 for these nights.')
  })
})
