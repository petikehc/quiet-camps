import { describe, expect, it } from 'vitest'
import { addDays, isOldSearchLink, parseFilters, parseView } from './filters'

const wednesday = new Date(2026, 10, 18) // months count from 0: 18 Nov 2026

describe('parseFilters', () => {
  it('defaults to the coming weekend, Friday and Saturday nights', () => {
    expect(parseFilters({}, wednesday)).toEqual({ arrive: '2026-11-20', depart: '2026-11-22' })
  })

  it('starts the default weekend today on a Friday', () => {
    expect(parseFilters({}, new Date(2026, 10, 20)).arrive).toBe('2026-11-20')
  })

  it('keeps the dates in the URL', () => {
    const filters = parseFilters({ arrive: '2027-04-02', depart: '2027-04-06' }, wednesday)
    expect(filters).toMatchObject({ arrive: '2027-04-02', depart: '2027-04-06' })
  })

  it('leaves two nights after a given arrival, across a month end', () => {
    expect(parseFilters({ arrive: '2027-01-31' }, wednesday).depart).toBe('2027-02-02')
  })

  it('replaces dates that are not real dates', () => {
    for (const arrive of ['2027-02-30', 'tomorrow', 20270402, '2027-4-2']) {
      expect(parseFilters({ arrive }, wednesday).arrive).toBe('2026-11-20')
    }
  })

  it('keeps an inverted range for the API to reject', () => {
    const filters = parseFilters({ arrive: '2027-04-06', depart: '2027-04-02' }, wednesday)
    expect(filters).toMatchObject({ arrive: '2027-04-06', depart: '2027-04-02' })
  })

  it('reads text filters, including numbers the router parsed', () => {
    expect(parseFilters({ q: ' fraser ', park: 1770 }, wednesday)).toMatchObject({
      q: 'fraser',
      park: '1770',
    })
  })

  it('drops blank and non-text filters', () => {
    const filters = parseFilters({ q: '   ', park: { name: 'x' } }, wednesday)
    expect(filters.q).toBeUndefined()
    expect(filters.park).toBeUndefined()
  })
})

describe('parseView', () => {
  it('turns on the location review', () => {
    expect(parseView({ review: 'locations' })).toEqual({ review: 'locations' })
  })

  it('ignores anything else', () => {
    expect(parseView({ review: 'everything' })).toEqual({})
    expect(parseView({})).toEqual({})
  })
})

describe('addDays', () => {
  it('crosses a leap day', () => {
    expect(addDays('2028-02-28', 1)).toBe('2028-02-29')
    expect(addDays('2028-02-28', 2)).toBe('2028-03-01')
  })
})

describe('isOldSearchLink', () => {
  it('spots a search link from when the search was the homepage', () => {
    expect(isOldSearchLink({ arrive: '2027-04-02', depart: '2027-04-06' })).toBe(true)
    expect(isOldSearchLink({ park: 'Main Range National Park' })).toBe(true)
    expect(isOldSearchLink({ review: 'locations' })).toBe(true)
  })

  it('leaves the homepage alone', () => {
    expect(isOldSearchLink({})).toBe(false)
    expect(isOldSearchLink({ utm_source: 'newsletter' })).toBe(false)
  })
})
