import { useInfiniteQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { unwrap } from '../api/errors'
import type { Filters } from './filters'

const PAGE_SIZE = 50

// One cache entry per set of filters, each a list of pages joined by the API's `next` cursor.
export function useQuietSearch(filters: Filters) {
  return useInfiniteQuery({
    queryKey: ['campgrounds', 'quiet', filters],
    queryFn: ({ pageParam, signal }) =>
      unwrap(
        api.GET('/campgrounds/quiet', {
          params: { query: { ...filters, limit: PAGE_SIZE, after: pageParam } },
          signal, // Query aborts the request when the filters change before it finishes
        }),
      ),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.next ?? undefined, // undefined: no more pages
  })
}
