import type { components } from '../api/schema'

export type Holiday = components['schemas']['HolidayOut']

// The holiday a night falls in, if any: nights count from the year's first night.
export function holidayOn(holidays: Holiday[], night: number): Holiday | undefined {
  return holidays.find((h) => night >= h.night && night < h.night + h.nights)
}

// The YYYY-MM-DD of a night, counted from the first night of the year.
export function nightDate(firstNight: string, night: number): string {
  const date = new Date(`${firstNight}T00:00:00Z`)
  date.setUTCDate(date.getUTCDate() + night)
  return date.toISOString().slice(0, 10)
}
