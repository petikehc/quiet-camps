import { nightDate } from './dates'

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

// The busiest nights, at least `gap` nights apart so each is its own moment, in night order:
// the peaks a year strip names. A night with no value is never a peak.
export function peaks(values: (number | null)[], count: number, gap: number): number[] {
  const picked: number[] = []
  const known = [...values.keys()].filter((n) => values[n] !== null)
  const byBusiest = known.sort((a, b) => (values[b] ?? 0) - (values[a] ?? 0) || a - b)
  for (const night of byBusiest) {
    if (picked.length === count) break
    if (picked.every((p) => Math.abs(p - night) >= gap)) picked.push(night)
  }
  return picked.sort((a, b) => a - b)
}

// Where each month starts among `nights` nights from firstNight, for the strip's labels.
export function monthStarts(firstNight: string, nights: number): { night: number; month: string }[] {
  const starts: { night: number; month: string }[] = []
  for (let n = 0; n < nights; n++) {
    const date = nightDate(firstNight, n)
    if (date.endsWith('-01')) starts.push({ night: n, month: MONTHS[Number(date.slice(5, 7)) - 1] })
  }
  return starts
}

export type Label = { night: number; text: string }
export type PlacedLabel = Label & { row: 0 | 1; align: 'start' | 'centre' | 'end' }

const LABEL_GAP = 8 // px between two labels on a row

// Labels over a strip `width` px wide, each centred on its night, or starting or ending there
// near an end so it stays over the strip: a label that would overlap one already placed goes to
// a second row, and one that would overlap there too is left out. Earlier labels win, so pass
// the most important first. Before the strip has a width, all centred on one row.
export function placeLabels(labels: Label[], last: number, width: number, charPx: number): PlacedLabel[] {
  if (width === 0) return labels.map((l) => ({ ...l, row: 0, align: 'centre' }))
  const taken: [number, number][][] = [[], []]
  const placed: PlacedLabel[] = []
  for (const label of labels) {
    const at = (label.night / Math.max(1, last)) * width
    const wide = label.text.length * charPx
    const align = at - wide / 2 < 0 ? 'start' : at + wide / 2 > width ? 'end' : 'centre'
    const start = { start: at, centre: at - wide / 2, end: at - wide }[align]
    const span: [number, number] = [start - LABEL_GAP / 2, start + wide + LABEL_GAP / 2]
    const row = taken.findIndex((spans) => spans.every(([a, b]) => span[1] <= a || span[0] >= b))
    if (row === -1) continue
    taken[row].push(span)
    placed.push({ ...label, row: row as 0 | 1, align })
  }
  return placed
}
