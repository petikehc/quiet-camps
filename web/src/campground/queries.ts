import { queryOptions } from '@tanstack/react-query'
import { api } from '../api/client'
import { unwrap } from '../api/errors'

// queryOptions keeps each key next to its fetch, typed, for useQuery (and loaders, later).
const path = (campgroundId: number) => ({ path: { campground_id: campgroundId } })

export const campgroundQuery = (id: number) =>
  queryOptions({
    queryKey: ['campground', id],
    queryFn: ({ signal }) =>
      unwrap(api.GET('/campgrounds/{campground_id}', { params: path(id), signal })),
  })

export const calendarQuery = (id: number, year: number) =>
  queryOptions({
    queryKey: ['campground', id, 'calendar', year],
    queryFn: ({ signal }) =>
      unwrap(
        api.GET('/campgrounds/{campground_id}/calendar', {
          params: { ...path(id), query: { year } },
          signal,
        }),
      ),
  })

export const leadTimeQuery = (id: number) =>
  queryOptions({
    queryKey: ['campground', id, 'lead-time'],
    queryFn: ({ signal }) =>
      unwrap(api.GET('/campgrounds/{campground_id}/lead-time', { params: path(id), signal })),
  })

export const yearsQuery = (id: number) =>
  queryOptions({
    queryKey: ['campground', id, 'years'],
    queryFn: ({ signal }) =>
      unwrap(api.GET('/campgrounds/{campground_id}/years', { params: path(id), signal })),
  })
