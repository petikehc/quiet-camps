// The search's filters live in the URL, so a search can be shared, bookmarked and gone back to.
// The router hands validateSearch whatever is in the query string; parseFilters makes it Filters.
// Range rules (depart after arrive, 60 nights at most) stay in the API: its 422 is shown as is.

export type Filters = {
  arrive: string // YYYY-MM-DD, the first night
  depart: string // YYYY-MM-DD, the morning you leave
  q?: string // part of a campground or park name
  park?: string // an exact park name
}

export function parseFilters(search: Record<string, unknown>, today = new Date()): Filters {
  const arrive = isoDate(search.arrive) ?? comingFriday(today)
  return {
    arrive,
    depart: isoDate(search.depart) ?? addDays(arrive, 2),
    q: text(search.q),
    park: text(search.park),
  }
}

export function addDays(day: string, days: number): string {
  const [year, month, date] = day.split('-').map(Number)
  // UTC, so a daylight-saving change can't move the date.
  return new Date(Date.UTC(year, month - 1, date + days)).toISOString().slice(0, 10)
}

function comingFriday(today: Date): string {
  const local = new Date(today.getFullYear(), today.getMonth(), today.getDate())
  local.setDate(local.getDate() + ((5 - local.getDay() + 7) % 7))
  return [local.getFullYear(), local.getMonth() + 1, local.getDate()]
    .map((part) => String(part).padStart(2, '0'))
    .join('-')
}

function isoDate(value: unknown): string | undefined {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return undefined
  return addDays(value, 0) === value ? value : undefined // 2027-02-30 rolls over, so it's not a date
}

function text(value: unknown): string | undefined {
  // The router JSON-parses query values, so ?q=1770 arrives as a number.
  if (typeof value === 'number') return String(value)
  if (typeof value !== 'string') return undefined
  return value.trim() || undefined
}
