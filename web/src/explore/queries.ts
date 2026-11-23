import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import type { components } from '../api/schema'
import { unwrap } from '../api/errors'
import { apiQuery, type Filters } from './filters'

export type QuietCampground = components['schemas']['QuietCampgroundOut']
export type Place = components['schemas']['PlaceOut']

// Every campground for the filters at once, quietest first (550 at most, ~25 KB gzipped):
// the bands, the list and the map all come from this one answer.
export function useQuietMap(filters: Filters) {
  const query = apiQuery(filters)
  return useQuery({
    queryKey: ['campgrounds', 'quiet', 'map', query],
    queryFn: ({ signal }) =>
      unwrap(api.GET('/campgrounds/quiet/map', { params: { query }, signal })),
    placeholderData: keepPreviousData, // the old pins stay while new ones load
  })
}

// Places by name for the place field: the ABS's towns and council areas, our parks and camps.
export function usePlaces(q: string) {
  const trimmed = q.trim()
  return useQuery({
    queryKey: ['places', trimmed.toLowerCase()],
    queryFn: ({ signal }) =>
      unwrap(api.GET('/places', { params: { query: { q: trimmed, limit: 6 } }, signal })),
    enabled: trimmed.length >= 2,
    staleTime: Infinity, // the places change once a census
  })
}

// A year of typical busyness for the campgrounds the filters pick (all but the dates), for the
// year strip. The answer depends on the place, not the nights, so moving dates reuses it.
export function useAreaYear(filters: Filters, year: number) {
  const { arrive: _arrive, depart: _depart, ...place } = apiQuery(filters)
  return useQuery({
    queryKey: ['campgrounds', 'quiet', 'year', year, place],
    queryFn: ({ signal }) =>
      unwrap(api.GET('/campgrounds/quiet/year', { params: { query: { ...place, year } }, signal })),
    staleTime: 60 * 60_000, // the history changes once a quarter
  })
}
