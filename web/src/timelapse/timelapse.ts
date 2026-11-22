import type { components } from '../api/schema'
import { FIRST_YEAR } from '../campground/year'
import { projection } from '../projection'

export type Year = components['schemas']['YearOut']
export type Holiday = components['schemas']['HolidayOut']

// ?year= on /timelapse: 2011 to this year (the API has no history after that). Anything else is
// last year, the latest year with every night.
export function parseTimelapseYear(
  search: Record<string, unknown>,
  today = new Date(),
): { year: number } {
  const { year } = search
  const latest = today.getFullYear()
  if (typeof year === 'number' && Number.isInteger(year) && year >= FIRST_YEAR && year <= latest) {
    return { year }
  }
  return { year: latest - 1 }
}

export function timelapseYears(today = new Date()): number[] {
  return Array.from({ length: today.getFullYear() - FIRST_YEAR + 1 }, (_, i) => FIRST_YEAR + i)
}

// Queensland's middle, so the state keeps its shape.
export const project = projection({ lon: 145.8, lat: -19.6 })

// Campers on each night, every campground together (located or not).
export function statewide(year: Year): number[] {
  const totals = new Array<number>(year.nights).fill(0)
  year.values.forEach((campers, i) => {
    totals[i % year.nights] += campers
  })
  return totals
}

// Each campground's busiest night that year: its 100% for the column colours.
export function peaks(year: Year): number[] {
  return year.campgrounds.map((_, row) =>
    Math.max(...year.values.slice(row * year.nights, (row + 1) * year.nights)),
  )
}

export function holidayOn(holidays: Holiday[], night: number): Holiday | undefined {
  return holidays.find((h) => night >= h.night && night < h.night + h.nights)
}

// The YYYY-MM-DD of a night, counted from the first night of the year.
export function nightDate(firstNight: string, night: number): string {
  const date = new Date(`${firstNight}T00:00:00Z`)
  date.setUTCDate(date.getUTCDate() + night)
  return date.toISOString().slice(0, 10)
}
