import type { components } from '../api/schema'
import { holidayOn, type Holiday } from '../charts/dates'

export type AreaYear = components['schemas']['AreaYearOut']

// The next 365 nights from today, from the year view of this year and the next: how busy the
// campgrounds asked about usually are each night, and the holidays among them.
export type ComingYear = {
  firstNight: string // today
  values: (number | null)[]
  holidays: Holiday[] // nights counted from today
}

const NIGHTS = 365
const DAY_MS = 86_400_000

export function nightsBetween(from: string, to: string): number {
  return Math.round((Date.parse(`${to}T00:00:00Z`) - Date.parse(`${from}T00:00:00Z`)) / DAY_MS)
}

export function comingYear(today: string, years: AreaYear[]): ComingYear {
  const values: (number | null)[] = []
  const holidays: Holiday[] = []
  for (const year of years) {
    const start = values.length
    values.push(...year.busyness)
    holidays.push(...year.holidays.map((h) => ({ ...h, night: h.night + start })))
  }
  const offset = nightsBetween(years[0]?.first_night ?? today, today)
  return {
    firstNight: today,
    values: values.slice(offset, offset + NIGHTS),
    holidays: holidays
      .map((h) => ({ ...h, night: h.night - offset }))
      .filter((h) => h.night + h.nights > 0 && h.night < NIGHTS)
      .map((h) => (h.night < 0 ? { ...h, night: 0, nights: h.nights + h.night } : h)),
  }
}

// The 7 nights with the lowest mean busyness, where every night has a value: the quietest
// week coming, to point at.
export function quietestWeek(values: (number | null)[]): number | undefined {
  let best: number | undefined
  let bestMean = Infinity
  for (let n = 0; n + 7 <= values.length; n++) {
    const week = values.slice(n, n + 7)
    if (week.some((v) => v === null)) continue
    const mean = week.reduce<number>((sum, v) => sum + (v ?? 0), 0) / 7
    if (mean < bestMean) [best, bestMean] = [n, mean]
  }
  return best
}

// The holiday a day falls in, if it's in the coming year.
export function holidayFor(coming: ComingYear, day: string): Holiday | undefined {
  return holidayOn(coming.holidays, nightsBetween(coming.firstNight, day))
}
