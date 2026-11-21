import { useInfiniteQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { ApiError } from '../api/errors'
import type { Filters } from './filters'

const PAGE_SIZE = 50

// One cache entry per set of filters, each a list of pages joined by the API's `next` cursor.
export function useQuietSearch(filters: Filters) {
  return useInfiniteQuery({
    queryKey: ['campgrounds', 'quiet', filters],
    queryFn: async ({ pageParam, signal }) => {
      const { data, error, response } = await api.GET('/campgrounds/quiet', {
        params: { query: { ...filters, limit: PAGE_SIZE, after: pageParam } },
        signal, // Query aborts the request when the filters change before it finishes
      })
      if (data === undefined) throw new ApiError(response.status, error)
      return data
    },
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.next ?? undefined, // undefined: no more pages
    retry: (failures, error) => !(error instanceof ApiError && error.status < 500) && failures < 3,
  })
}
