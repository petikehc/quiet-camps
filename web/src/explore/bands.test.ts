import { describe, expect, it } from 'vitest'
import { bandNote, bandOf, ordinal, rankWords, soundSwell, usually } from './bands'

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
  it('says booked sites on these nights in past years, against its busiest nights', () => {
    expect(usually({ typical_sites: 2.4, busy_night_sites: 40 })).toBe(
      'These nights: usually 2 sites booked in past years. Its busiest nights: about 40.',
    )
    expect(usually({ typical_sites: 1, busy_night_sites: 7 })).toBe(
      'These nights: usually 1 site booked in past years. Its busiest nights: about 7.',
    )
  })

  it('says no sites, in past years, so it never reads as free', () => {
    expect(usually({ typical_sites: 0.2, busy_night_sites: 26 })).toBe(
      'These nights: usually no sites booked in past years. Its busiest nights: about 26.',
    )
  })

  it("says when these nights pass its usual busiest nights, so usual isn't over busy", () => {
    expect(usually({ typical_sites: 51, busy_night_sites: 36 })).toBe(
      'These nights: usually 51 sites booked in past years, more than on its usual busiest nights (36).',
    )
    expect(usually({ typical_sites: 36.2, busy_night_sites: 36 })).toBe(
      'These nights: usually 36 sites booked in past years, as many as on its busiest nights.',
    )
  })

  it('says a campground whose busiest nights have a site or two hardly ever has more', () => {
    expect(usually({ typical_sites: 0, busy_night_sites: 0 })).toBe(
      'Hardly ever more than 1 site booked',
    )
    expect(usually({ typical_sites: 1, busy_night_sites: 2 })).toBe(
      'Hardly ever more than 2 sites booked',
    )
  })
})

describe('bandNote', () => {
  it('says what each band means, from its thresholds, and what its busiest nights are', () => {
    expect(bandNote('quiet')).toBe(
      'In past years, under 25% as busy as its busiest nights (its busiest 1 night in 20).',
    )
    expect(bandNote('ok')).toBe(
      'In past years, 25–60% as busy as its busiest nights (its busiest 1 night in 20).',
    )
    expect(bandNote('busy')).toBe(
      'In past years, 60% as busy as its busiest nights or more (its busiest 1 night in 20).',
    )
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
  it('ranks within the band, from its quiet end, or its busy end for the busy band', () => {
    expect(rankWords('quiet', 1, 5)).toBe('The quietest of 5 quiet ones for these nights.')
    expect(rankWords('quiet', 3, 5)).toBe('3rd quietest of 5 quiet ones for these nights.')
    expect(rankWords('ok', 2, 9)).toBe('2nd quietest of 9 not too busy ones for these nights.')
    expect(rankWords('busy', 1, 32)).toBe('The busiest of 32 busy ones for these nights.')
    expect(rankWords('busy', 4, 32)).toBe('4th busiest of 32 busy ones for these nights.')
  })

  it('says when it is the only one in its band', () => {
    expect(rankWords('quiet', 1, 1)).toBe('The only quiet one for these nights.')
  })
})

describe('soundSwell', () => {
  it('is silent for quiet nights and full for busy ones, as the bands are', () => {
    expect(soundSwell([0.1, 0.2, null], 0, 3)).toBe(0) // usually quiet
    expect(soundSwell([0.7, 0.9], 0, 2)).toBe(1) // usually busy
    expect(soundSwell([0.1, 0.425, 0.1], 1, 2)).toBeCloseTo(0.5) // halfway between the bands' edges
  })

  it('is the quiet bed when no night has a value', () => {
    expect(soundSwell([null, null], 0, 2)).toBe(0)
  })
})
