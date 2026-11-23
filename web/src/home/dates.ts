// Your dates on the homepage: shown on last year's map, and carried to the search.

const DAY_MS = 86_400_000

// The night in `year` with the same day and month as `day` (YYYY-MM-DD), counted from 1 January.
// 29 February becomes the 28th in a year without one.
export function sameNight(day: string, year: number): number {
  const [, month, date] = day.split('-').map(Number)
  const at = Date.UTC(year, month - 1, date)
  const rolled = new Date(at).getUTCMonth() !== month - 1 // 29 Feb rolls into March
  return (at - Date.UTC(year, 0, 1)) / DAY_MS - (rolled ? 1 : 0)
}

const ISO = /^\d{4}-\d{2}-\d{2}$/

// Both dates, and leaving after arriving. The search's own rules (60 nights at most) stay there.
export function isTrip(arrive: string, depart: string): boolean {
  return ISO.test(arrive) && ISO.test(depart) && depart > arrive
}

function part(day: string, options: Intl.DateTimeFormatOptions): string {
  return new Date(`${day}T00:00:00Z`).toLocaleDateString('en-AU', { ...options, timeZone: 'UTC' })
}

// "18–21 Apr", or "30 Apr – 3 May" across a month.
export function tripLabel(arrive: string, depart: string): string {
  const to = part(depart, { day: 'numeric', month: 'short' })
  if (arrive.slice(0, 7) === depart.slice(0, 7)) return `${part(arrive, { day: 'numeric' })}–${to}`
  return `${part(arrive, { day: 'numeric', month: 'short' })} – ${to}`
}
