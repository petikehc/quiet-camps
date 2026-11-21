// The calendar's years: the API serves 2011 (the first permits) to three years ahead.
export const FIRST_YEAR = 2011

export function lastYear(today = new Date()): number {
  return today.getFullYear() + 3
}

// ?year= in the campground page's URL; anything else is this year.
export function parseYear(search: Record<string, unknown>, today = new Date()): { year: number } {
  const { year } = search // the router JSON-parses it, so ?year=2025 arrives as a number
  if (typeof year === 'number' && Number.isInteger(year) && year >= FIRST_YEAR && year <= lastYear(today)) {
    return { year }
  }
  return { year: today.getFullYear() }
}
