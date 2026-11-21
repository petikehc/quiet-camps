import { getRouteApi } from '@tanstack/react-router'
import { lazy, Suspense, useEffect, useMemo, useRef, useState } from 'react'
import { fieldErrors } from '../api/errors'
import { ResultsTable, type QuietCampground } from './ResultsTable'
import { SearchForm } from './SearchForm'
import { useQuietSearch } from './useQuietSearch'

// getRouteApi instead of importing the route: router.tsx imports this file, not the other way.
const route = getRouteApi('/')
const noRows: QuietCampground[] = []

// MapLibre is most of the app's JavaScript: its own chunk, loaded only where a map is shown.
const ResultsMap = lazy(() => import('./ResultsMap').then((m) => ({ default: m.ResultsMap })))

export function SearchPage() {
  const filters = route.useSearch()
  const search = useQuietSearch(filters)
  // A new array only when a page arrives; the table rebuilds its rows when this changes.
  const rows = useMemo(() => search.data?.pages.flatMap((page) => page.results) ?? noRows, [search.data])
  // Shared by the map and the list: picking in one highlights (and brings into view) the other.
  const [selected, setSelected] = useState<{ id: number; from: 'map' | 'list' }>()

  return (
    <>
      <SearchForm filters={filters} />
      {/* Stays mounted between searches, so the tiles don't reload. Until its code arrives, an
          empty box the same size keeps the table from jumping. */}
      <Suspense fallback={<div className="results-map map-canvas" />}>
        <ResultsMap
          rows={rows}
          selectedId={selected?.id}
          onSelect={(id) => setSelected({ id, from: 'map' })}
          fitKey={JSON.stringify(filters)}
        />
      </Suspense>
      {search.isPending && <p role="status">Searching…</p>}
      {search.isError && <SearchError error={search.error} />}
      {search.isSuccess && rows.length === 0 && (
        <p>No campgrounds have enough history for these nights. Try other dates or names.</p>
      )}
      {rows.length > 0 && (
        <ResultsTable
          rows={rows}
          selectedId={selected?.id}
          onSelect={(id) => setSelected({ id, from: 'list' })}
          scrollToSelected={selected?.from === 'map'}
        />
      )}
      {search.hasNextPage && (
        <LoadMore
          loading={search.isFetchingNextPage}
          // cancelRefetch: false makes a call while a page is loading a no-op, not a restart.
          onLoad={() => void search.fetchNextPage({ cancelRefetch: false })}
        />
      )}
    </>
  )
}

function SearchError({ error }: { error: Error }) {
  const errors = fieldErrors(error)
  return (
    <div role="alert" className="error">
      <p>{errors.length > 0 ? 'Check the search:' : `The search failed: ${error.message}`}</p>
      {errors.length > 0 && (
        <ul>
          {errors.map((e) => (
            <li key={`${e.field}: ${e.message}`}>{e.message}</li>
          ))}
        </ul>
      )}
    </div>
  )
}

// Infinite scroll with a real button: it loads the next page as it nears the viewport, and
// still works by click or keyboard.
function LoadMore({ loading, onLoad }: { loading: boolean; onLoad: () => void }) {
  const button = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!button.current || loading) return
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) onLoad()
      },
      { rootMargin: '400px' }, // start before it's on screen
    )
    observer.observe(button.current)
    return () => observer.disconnect()
  }, [loading, onLoad])

  return (
    <button ref={button} type="button" className="load-more" disabled={loading} onClick={onLoad}>
      {loading ? 'Loading…' : 'Load more'}
    </button>
  )
}
