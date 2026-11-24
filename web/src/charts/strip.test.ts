import { describe, expect, it } from 'vitest'
import { monthStarts, peaks, placeLabels } from './strip'

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

describe('placeLabels', () => {
  // A year of 365 nights; Easter and "Quietest week" 43 nights apart, as near Noosa in 2027.
  const easter = { night: 121, text: 'Easter' }
  const quietest = { night: 164, text: 'Quietest week' }

  it('keeps labels on one row when there is room', () => {
    expect(placeLabels([easter, quietest], 364, 1000, 7)).toEqual([
      { ...easter, row: 0, align: 'centre' },
      { ...quietest, row: 0, align: 'centre' },
    ])
  })

  it('moves a label that would overlap to a second row on a narrow strip', () => {
    expect(placeLabels([easter, quietest], 364, 330, 7)).toEqual([
      { ...easter, row: 0, align: 'centre' },
      { ...quietest, row: 1, align: 'centre' },
    ])
  })

  it('drops a label that would overlap on both rows, keeping the earlier ones', () => {
    const anzac = { night: 140, text: 'Anzac Day' }

    expect(placeLabels([easter, quietest, anzac], 364, 330, 7)).toEqual([
      { ...easter, row: 0, align: 'centre' },
      { ...quietest, row: 1, align: 'centre' },
    ])
  })

  it('keeps a label near either end over the strip', () => {
    const kings = { night: 4, text: "King's Birthday" } // early October, at the strip's start
    const christmas = { night: 360, text: 'Christmas' }

    expect(placeLabels([kings, christmas], 364, 600, 7).map((l) => l.align)).toEqual(['start', 'end'])
  })

  it('places everything on one row before the strip has a width', () => {
    expect(placeLabels([easter, quietest], 364, 0, 7).map((l) => l.row)).toEqual([0, 0])
  })
})
