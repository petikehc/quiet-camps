// Pure helpers behind the charts, kept apart from the SVG so they can be unit-tested.

// Five bins of one sand-to-red-earth ramp (the colours are --heat-0 to --heat-4 in index.css). More than
// about seven classes blur together; five keep "quiet" and "busy" a glance apart.
export const HEAT_LABELS = ['Under 20%', '20–40%', '40–60%', '60–80%', '80% or more']

export function heatBin(share: number): number {
  return Math.min(HEAT_LABELS.length - 1, Math.max(0, Math.floor(share * HEAT_LABELS.length)))
}

const DAY_MS = 24 * 60 * 60 * 1000

// A night's place in a year calendar: one column per week (Monday first), one row per weekday.
export function calendarCell(night: string): { column: number; row: number } {
  const [year, month, date] = night.split('-').map(Number)
  const january1 = Date.UTC(year, 0, 1)
  const dayOfYear = (Date.UTC(year, month - 1, date) - january1) / DAY_MS
  const january1Weekday = (new Date(january1).getUTCDay() + 6) % 7 // Monday = 0
  const slot = january1Weekday + dayOfYear
  return { column: Math.floor(slot / 7), row: slot % 7 }
}

// Round axis ticks from 0: steps of 1, 2 or 5 times a power of ten, about `count` of them.
export function niceTicks(max: number, count = 4): number[] {
  if (max <= 0) return [0, 1]
  const rough = max / count
  const power = 10 ** Math.floor(Math.log10(rough))
  const step = Math.max(1, [1, 2, 5, 10].map((m) => m * power).find((s) => s >= rough) ?? power)
  const top = Math.ceil(max / step) * step
  return Array.from({ length: top / step + 1 }, (_, i) => i * step)
}

export function formatNight(night: string): string {
  return new Date(`${night}T00:00:00Z`).toLocaleDateString('en-AU', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone: 'UTC', // a YYYY-MM-DD is a calendar date, not a moment: no time zone may move it
  })
}

// The API names holidays in lower case ("sovereign's birthday"); show them as sentences.
export function holidayName(name: string): string {
  return name.charAt(0).toUpperCase() + name.slice(1)
}
