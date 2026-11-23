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
