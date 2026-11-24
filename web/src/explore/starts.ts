import type { Filters } from './filters'

export type Start = Required<Pick<Filters, 'near' | 'lat' | 'lon' | 'km'>>

// Where most campers set out from, for a search with no place yet: the ABS council points from
// the place table, the same points /ask resolves these names to, and its 150 km for "from".
const FROM_KM = 150
export const STARTS: Start[] = [
  { near: 'Brisbane', lat: -27.4406, lon: 152.8973, km: FROM_KM },
  { near: 'Gold Coast', lat: -28.0708, lon: 153.3605, km: FROM_KM },
  { near: 'Sunshine Coast', lat: -26.7078, lon: 152.8509, km: FROM_KM },
  { near: 'Toowoomba', lat: -27.5997, lon: 151.4771, km: FROM_KM },
  { near: 'Townsville', lat: -19.352, lon: 146.768, km: FROM_KM },
  { near: 'Cairns', lat: -17.2029, lon: 145.8439, km: FROM_KM },
]

// Where the browser says you are, if the search can use it: the API takes points in and around
// Australia's east (search.py's near_lat and near_lon).
export function startAt(lat: number, lon: number): Start | undefined {
  if (lat < -45 || lat > -9 || lon < 112 || lon > 155) return undefined
  return { near: 'your location', lat: Number(lat.toFixed(4)), lon: Number(lon.toFixed(4)), km: FROM_KM }
}
