import { describe, expect, it } from 'vitest'
import { summary } from './summary'

describe('summary', () => {
  it('says the holiday, the dates and the place', () => {
    expect(
      summary(
        { arrive: '2027-03-25', depart: '2027-03-29', near: 'Noosa', lat: -26.3, lon: 152.9, km: 50 },
        'Easter',
      ),
    ).toBe('Easter · Thu 25 – Mon 29 Mar · within 50 km of Noosa')
  })

  it('names both months when the stay crosses one, and anywhere with no place', () => {
    expect(summary({ arrive: '2027-01-31', depart: '2027-02-02' })).toBe(
      'Sun 31 Jan – Tue 2 Feb · anywhere in Queensland',
    )
  })

  it('names the park when the search is in one', () => {
    expect(summary({ arrive: '2026-11-27', depart: '2026-11-29', park: 'Main Range National Park' })).toBe(
      'Fri 27 – Sun 29 Nov · in Main Range National Park',
    )
  })
})
