// The search's filters live in the URL, so a search can be shared, bookmarked and gone back to.
// The router hands validateSearch whatever is in the query string; parseFilters makes it Filters.
// Range rules (depart after arrive, 60 nights at most) stay in the API: its 422 is shown as is.

export type Filters = {
  arrive: string // YYYY-MM-DD, the first night
  depart: string // YYYY-MM-DD, the morning you leave
  q?: string // part of a campground or park name
  park?: string // an exact park name
  // Within km of a place: where you set out from, or want to be near. All four, or none.
  near?: string // the place's name, as shown
  lat?: number
  lon?: number
  km?: number
}

export const KM_CHOICES = [25, 50, 100, 200]
const KM_RANGE = [10, 400] // the API's

export function parseFilters(search: Record<string, unknown>, today = new Date()): Filters {
  const arrive = isoDate(search.arrive) ?? comingFriday(today)
  return {
    arrive,
    depart: isoDate(search.depart) ?? addDays(arrive, 2),
    q: text(search.q),
    park: text(search.park),
    ...place(search),
  }
}

// A place in Australia, or none: a half-given or far-off place is dropped, not half-searched.
function place(search: Record<string, unknown>): Pick<Filters, 'near' | 'lat' | 'lon' | 'km'> {
  const lat = number(search.lat)
  const lon = number(search.lon)
  if (lat === undefined || lon === undefined) return {}
  if (lat < -45 || lat > -9 || lon < 112 || lon > 155) return {}
  const km = Math.min(KM_RANGE[1], Math.max(KM_RANGE[0], number(search.km) ?? 50))
  return { near: text(search.near) ?? 'the place on the map', lat, lon, km }
}

// The API's names for the filters.
export function apiQuery(f: Filters) {
  const near =
    f.lat === undefined || f.lon === undefined
      ? {}
      : { near_lat: f.lat, near_lon: f.lon, within_km: f.km ?? 50 }
  return { arrive: f.arrive, depart: f.depart, q: f.q, park: f.park, ...near }
}

// How busy campgrounds usually are on the nights asked for, against their own busy nights.
export type Band = 'quiet' | 'ok' | 'busy'
const BANDS: Band[] = ['quiet', 'ok', 'busy']

// Not filters (filters go to the API): which band the list shows, the campground picked, and
// ?review=locations, which shows how sure each location is.
export type View = { review?: 'locations'; band?: Band; sel?: number }

export function parseView(search: Record<string, unknown>): View {
  const band = BANDS.find((b) => b === search.band)
  const sel = number(search.sel)
  return {
    ...(search.review === 'locations' ? { review: 'locations' } : {}),
    ...(band ? { band } : {}),
    ...(sel !== undefined && Number.isInteger(sel) ? { sel } : {}),
  }
}

export function addDays(day: string, days: number): string {
  const [year, month, date] = day.split('-').map(Number)
  // UTC, so a daylight-saving change can't move the date.
  return new Date(Date.UTC(year, month - 1, date + days)).toISOString().slice(0, 10)
}

// Today's date where the browser is, YYYY-MM-DD.
export function localDay(today = new Date()): string {
  return [today.getFullYear(), today.getMonth() + 1, today.getDate()]
    .map((part) => String(part).padStart(2, '0'))
    .join('-')
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

function number(value: unknown): number | undefined {
  const n = typeof value === 'string' && value.trim() !== '' ? Number(value) : value
  return typeof n === 'number' && Number.isFinite(n) ? n : undefined
}

function text(value: unknown): string | undefined {
  // The router JSON-parses query values, so ?q=1770 arrives as a number.
  if (typeof value === 'number') return String(value)
  if (typeof value !== 'string') return undefined
  return value.trim() || undefined
}

// The search was the homepage until the trips map took /: its old links and bookmarks still
// carry these, and go on to /explore.
const SEARCH_KEYS = ['arrive', 'depart', 'q', 'park', 'review']

export function isOldSearchLink(search: Record<string, unknown>): boolean {
  return SEARCH_KEYS.some((key) => key in search)
}
