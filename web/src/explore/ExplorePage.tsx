import { getRouteApi } from '@tanstack/react-router'
import type * as maplibregl from 'maplibre-gl'
import { lazy, Suspense, useEffect, useMemo, useRef, useState } from 'react'
import { fieldErrors } from '../api/errors'
import { BandToggle } from './BandToggle'
import { BAND_NAMES, bandOf } from './bands'
import { Card } from './Card'
import { comingYear, holidayFor } from './comingYear'
import { apiQuery, localDay, type Band, type Filters } from './filters'
import { LeaderLine } from './LeaderLine'
import { QueryBar } from './QueryBar'
import { useAreaYear, useQuietMap } from './queries'
import { WhenStrip } from './WhenStrip'

// MapLibre is most of the page's weight: the list can show before it arrives.
const ExploreMap = lazy(() =>
  import('./ExploreMap').then((module) => ({ default: module.ExploreMap })),
)

const route = getRouteApi('/explore')
const SHOWN = 40 // cards at first; "Show more" adds as many again

// The map of Queensland's campgrounds for some nights, with the quiet ones (or the not too
// busy, or the busy) listed beside it.
export function ExplorePage() {
  const search = route.useSearch()
  const navigate = route.useNavigate()
  const { review, band = 'quiet', sel, ...filters } = search
  const query = useQuietMap(filters)
  const rows = useMemo(() => query.data?.results ?? [], [query.data])
  // The coming year for these campgrounds: this year's view and next year's, joined at today.
  const today = localDay()
  const thisYear = useAreaYear(filters, Number(today.slice(0, 4)))
  const nextYear = useAreaYear(filters, Number(today.slice(0, 4)) + 1)
  const coming = useMemo(
    () => (thisYear.data && nextYear.data ? comingYear(today, [thisYear.data, nextYear.data]) : undefined),
    [today, thisYear.data, nextYear.data],
  )

  const counts = useMemo(() => {
    const counted: Record<Band, number> = { quiet: 0, ok: 0, busy: 0 }
    for (const r of rows) counted[bandOf(r.busyness)]++
    return counted
  }, [rows])
  // Quietest first; the busy list busiest first, which is what it's for.
  const listed = useMemo(() => {
    const inBand = rows.filter((r) => bandOf(r.busyness) === band)
    return band === 'busy' ? inBand.reverse() : inBand
  }, [rows, band])

  const [shown, setShown] = useState(SHOWN)
  const [hovered, setHovered] = useState<number>()
  const [map, setMap] = useState<maplibregl.Map>()
  const root = useRef<HTMLDivElement>(null)
  const list = useRef<HTMLOListElement>(null)
  const fitKey = JSON.stringify(apiQuery(filters))

  function setFilters(next: Filters) {
    setShown(SHOWN)
    void navigate({ search: { ...next, ...(review ? { review } : {}), band } })
  }

  function setBand(next: Band) {
    setShown(SHOWN)
    void navigate({ search: (prev) => ({ ...prev, band: next, sel: undefined }), replace: true })
  }

  // Picked on the map or the list: its band is listed, and picking it again closes it.
  function select(id: number) {
    const row = rows.find((r) => r.id === id)
    void navigate({
      search: (prev) => ({
        ...prev,
        sel: prev.sel === id ? undefined : id,
        band: row ? bandOf(row.busyness) : prev.band,
      }),
      replace: true,
    })
  }

  // A pick on the map brings its card into the list, and into view.
  const visible = Math.max(shown, listed.findIndex((r) => r.id === sel) + 1)
  useEffect(() => {
    if (sel === undefined) return
    root.current
      ?.querySelector(`[data-id="${sel}"]`)
      ?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }, [sel])

  const active = rows.find((r) => r.id === (hovered ?? sel))
  const near =
    filters.lat !== undefined && filters.lon !== undefined
      ? { lat: filters.lat, lon: filters.lon, km: filters.km ?? 50 }
      : undefined
  const holiday = coming && holidayFor(coming, filters.arrive)

  return (
    <div className="explore" ref={root}>
      <aside className="explore-side" aria-label="Campgrounds">
        <QueryBar filters={filters} onChange={setFilters} />
        <BandToggle band={band} counts={counts} onChange={setBand} />
        {query.isError && <ExploreError error={query.error} />}
        {query.isPending && <p className="explore-status">Finding campgrounds…</p>}
        {query.isSuccess && listed.length === 0 && (
          <p className="explore-status">{emptyWords(band, rows.length, filters)}</p>
        )}
        <ol className={`explore-cards band-${band}`} ref={list} aria-busy={query.isFetching}>
          {listed.slice(0, visible).map((c) => (
            <Card
              key={c.id}
              campground={c}
              selected={c.id === sel}
              rank={rows.indexOf(c) + 1}
              of={rows.length}
              arrive={filters.arrive}
              holiday={holiday}
              today={today}
              review={review !== undefined}
              onSelect={() => select(c.id)}
              onHover={(on) => setHovered(on ? c.id : undefined)}
            />
          ))}
          {listed.length > visible && (
            <li className="show-more">
              <button type="button" onClick={() => setShown(visible + SHOWN)}>
                Show more ({listed.length - visible} more {BAND_NAMES[band].toLowerCase()})
              </button>
            </li>
          )}
        </ol>
        <footer className="explore-credits">
          Past bookings, not live availability. Camping permits © State of Queensland; places and
          boundaries © Commonwealth of Australia (ABS), CC BY 4.0. Map © OpenStreetMap
          contributors. Not affiliated with Queensland Parks and Wildlife Service.
        </footer>
      </aside>
      <Suspense fallback={<div className="explore-map" />}>
        <ExploreMap
          rows={rows}
          band={band}
          selectedId={sel}
          highlightId={hovered}
          onSelect={select}
          near={near}
          fitKey={fitKey}
          review={review !== undefined}
          onMap={setMap}
        />
      </Suspense>
      {coming && (
        <WhenStrip
          coming={coming}
          arrive={filters.arrive}
          depart={filters.depart}
          near={filters.near}
          onDates={(arrive, depart) => setFilters({ ...filters, arrive, depart })}
        />
      )}
      <LeaderLine
        map={map}
        root={root}
        list={list}
        id={active?.id}
        lat={active?.lat}
        lon={active?.lon}
      />
    </div>
  )
}

function emptyWords(band: Band, total: number, filters: Filters): string {
  const where = filters.near ? ` within ${filters.km} km of ${filters.near}` : ''
  if (total === 0) return `No campgrounds${where} are usually open on these nights.`
  return `None${where} are usually ${BAND_NAMES[band].toLowerCase()} on these nights: try the other bands, or other dates.`
}

function ExploreError({ error }: { error: Error }) {
  const errors = fieldErrors(error)
  return (
    <div role="alert" className="error">
      <p>{errors.length > 0 ? 'Check the dates:' : "The campgrounds didn't load. Try again soon."}</p>
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
