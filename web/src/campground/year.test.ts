import { describe, expect, it } from 'vitest'
import { parseYear } from './year'

const today = new Date(2026, 10, 21)

describe('parseYear', () => {
  it('keeps a year the API serves', () => {
    expect(parseYear({ year: 2011 }, today)).toEqual({ year: 2011 })
    expect(parseYear({ year: 2029 }, today)).toEqual({ year: 2029 })
  })

  it('defaults to this year', () => {
    expect(parseYear({}, today)).toEqual({ year: 2026 })
  })

  it('replaces years outside 2011 to three years ahead', () => {
    expect(parseYear({ year: 2010 }, today)).toEqual({ year: 2026 })
    expect(parseYear({ year: 2030 }, today)).toEqual({ year: 2026 })
  })

  it('replaces years that are not whole numbers', () => {
    for (const year of ['2025', 2025.5, null]) expect(parseYear({ year }, today)).toEqual({ year: 2026 })
  })
})
