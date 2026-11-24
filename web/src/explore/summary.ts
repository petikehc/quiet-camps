import type { Filters } from './filters'

function day(date: string, withMonth: boolean): string {
  return new Date(`${date}T00:00:00Z`).toLocaleDateString('en-AU', {
    weekday: 'short',
    day: 'numeric',
    ...(withMonth ? { month: 'short' } : {}),
    timeZone: 'UTC',
  }).replace(',', '') // en-AU says "Mon, 29 Mar"
}

// The search in one line, for a phone, where the fields fold away: "Easter · Thu 25 – Mon 29 Mar
// · within 50 km of Noosa".
export function summary(filters: Filters, holiday?: string): string {
  const sameMonth = filters.arrive.slice(0, 7) === filters.depart.slice(0, 7)
  const dates = `${day(filters.arrive, !sameMonth)} – ${day(filters.depart, true)}`
  const where = filters.near
    ? `within ${filters.km} km of ${filters.near}`
    : filters.park
      ? `in ${filters.park}`
      : 'anywhere in Queensland'
  return [holiday, dates, where].filter(Boolean).join(' · ')
}
