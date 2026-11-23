import { describe, expect, it } from 'vitest'
import { bandOf, usually } from './bands'

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
  it('says booked sites against its busy nights', () => {
    expect(usually({ typical_sites: 2.4, busy_night_sites: 40 })).toBe(
      'Usually 2 sites booked · 40 on its busy nights',
    )
    expect(usually({ typical_sites: 1, busy_night_sites: 7 })).toBe(
      'Usually 1 site booked · 7 on its busy nights',
    )
  })

  it('says none when a typical night has nothing booked', () => {
    expect(usually({ typical_sites: 0.2, busy_night_sites: 26 })).toBe(
      'Usually none booked · 26 on its busy nights',
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
