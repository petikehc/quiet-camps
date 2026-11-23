import { describe, expect, it } from 'vitest'
import { monthStarts, peaks } from './strip'

describe('peaks', () => {
  const totals = [1, 9, 8, 2, 1, 7, 3, 6, 1, 1]

  it('takes the busiest nights at least `gap` apart, in night order', () => {
    expect(peaks(totals, 3, 3)).toEqual([1, 5, 8])
  })

  it('skips a night too close to a busier one', () => {
    expect(peaks(totals, 2, 3)).not.toContain(2) // 8, but beside the 9
  })

  it('stops short when no more nights are far enough apart', () => {
    expect(peaks(totals, 5, 6)).toEqual([1, 7])
  })
})

describe('peaks with gaps', () => {
  it('never picks a night with no value', () => {
    expect(peaks([null, 2, null, 1], 2, 1)).toEqual([1, 3])
  })
})

describe('monthStarts', () => {
  it('finds each first of the month, across a year end', () => {
    expect(monthStarts('2026-11-24', 70)).toEqual([
      { night: 7, month: 'Dec' },
      { night: 38, month: 'Jan' },
      { night: 69, month: 'Feb' },
    ])
  })
})
