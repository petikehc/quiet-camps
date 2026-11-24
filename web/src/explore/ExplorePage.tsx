import { getRouteApi } from '@tanstack/react-router'
import type * as maplibregl from 'maplibre-gl'
import { lazy, Suspense, useEffect, useMemo, useRef, useState } from 'react'
import { fieldErrors } from '../api/errors'
import { nightDate } from '../charts/dates'
import { holidayName } from '../charts/scales'
import { BandToggle } from './BandToggle'
import { BAND_NAMES, bandNote, bandOf } from './bands'
import { Card } from './Card'
import { comingYear, holidayFor, nightsBetween, quietestWeek, type ComingYear } from './comingYear'
import { addDays, apiQuery, localDay, widerKm, type Band, type Filters } from './filters'
import { LeaderLine } from './LeaderLine'
import { QueryBar } from './QueryBar'
import { useAreaYear, useQuietMap } from './queries'
import { STARTS, startAt, type Start } from './starts'
import { dateRange, summary } from './summary'
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
  const [editing, setEditing] = useState(false) // on a phone, the fields fold under a summary
  const root = useRef<HTMLDivElement>(null)
  const list = useRef<HTMLOListElement>(null)
  const fitKey = JSON.stringify(apiQuery(filters))

  // Each change is a step Back can undo, except dragging the strip, which would be dozens.
  function setFilters(next: Filters, replace = false) {
    setShown(SHOWN)
    void navigate({ search: { ...next, ...(review ? { review } : {}), band }, replace })
  }

  function setBand(next: Band) {
    setShown(SHOWN)
    void navigate({ search: (prev) => ({ ...prev, band: next, sel: undefined }) })
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
      <section className={editing ? 'explore-query editing' : 'explore-query'} aria-label="Where and when">
        <div className="query-summary">
          <p>{summary(filters, holiday && holidayName(holiday.name))}</p>
          <button
            type="button"
            className="link-button"
            aria-expanded={editing}
            aria-controls="query-fields"
            onClick={() => setEditing(!editing)}
          >
            {editing ? 'Done' : 'Change'}
          </button>
        </div>
        <div id="query-fields">
          <QueryBar filters={filters} onChange={setFilters} />
        </div>
      </section>
      <aside className="explore-side" aria-label="Campgrounds">
        <BandToggle band={band} counts={counts} onChange={setBand} />
        <p className="band-note">{bandNote(band)}</p>
        <p className="visually-hidden" aria-live="polite">
          {query.isSuccess && `${counts[band]} ${BAND_NAMES[band].toLowerCase()} campgrounds`}
        </p>
        {filters.near === undefined && !filters.park && (
          <WhereFrom onPick={(start) => setFilters({ ...filters, ...start })} />
        )}
        {query.isError && (
          <ExploreError error={query.error} onRetry={() => void query.refetch()} />
        )}
        {query.isPending && <p className="explore-status">Finding campgrounds…</p>}
        {query.isSuccess && listed.length === 0 && (
          <Empty
            band={band}
            counts={counts}
            filters={filters}
            coming={coming}
            onBand={setBand}
            onFilters={setFilters}
          />
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
      </aside>
      <footer className="explore-credits">
        Past bookings, not live availability. Camping permits © State of Queensland; places and
        boundaries © Commonwealth of Australia (ABS), CC BY 4.0. Map © OpenStreetMap
        contributors. Not affiliated with Queensland Parks and Wildlife Service.
      </footer>
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
          onDates={(arrive, depart) => setFilters({ ...filters, arrive, depart }, true)}
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

// A search with no place yet: most campers set out from a city, or from where they are.
function WhereFrom({ onPick }: { onPick: (start: Start) => void }) {
  const [note, setNote] = useState<string>()

  function nearMe() {
    setNote('Finding where you are…')
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        const start = startAt(coords.latitude, coords.longitude)
        setNote(start ? undefined : "That's too far from Queensland to search from: pick a town.")
        if (start) onPick(start)
      },
      () => setNote("Couldn't get your location: pick a town, or type one above."),
      { maximumAge: 600_000, timeout: 10_000 },
    )
  }

  return (
    <div className="where-from">
      <p>Where from? Campgrounds within 150 km:</p>
      <div className="chips">
        {STARTS.map((start) => (
          <button key={start.near} type="button" className="chip-button" onClick={() => onPick(start)}>
            {start.near}
          </button>
        ))}
        {'geolocation' in navigator && (
          <button type="button" className="chip-button" onClick={nearMe}>
            Near me
          </button>
        )}
      </div>
      {note && (
        <p className="where-note" role="status">
          {note}
        </p>
      )}
    </div>
  )
}

type EmptyProps = {
  band: Band
  counts: Record<Band, number>
  filters: Filters
  coming: ComingYear | undefined
  onBand: (band: Band) => void
  onFilters: (filters: Filters) => void
}

// Nothing in this band: what is there instead, one tap away.
function Empty({ band, counts, filters, coming, onBand, onFilters }: EmptyProps) {
  const total = counts.quiet + counts.ok + counts.busy
  const where = filters.near ? ` within ${filters.km} km of ${filters.near}` : ''
  const wider = filters.near && filters.km !== undefined ? widerKm(filters.km) : undefined
  const others = (['quiet', 'ok', 'busy'] as const).filter((b) => b !== band && counts[b] > 0)
  const week = coming && quietestWeek(coming.values)
  const stay = nightsBetween(filters.arrive, filters.depart)
  const quietArrive = week !== undefined && coming ? nightDate(coming.firstNight, week) : undefined

  return (
    <div className="explore-status">
      <p>
        {total === 0
          ? `No campgrounds${where} are usually open on these nights.`
          : `None${where} are usually ${BAND_NAMES[band].toLowerCase()} on these nights.`}
      </p>
      <div className="chips">
        {others.map((b) => (
          <button key={b} type="button" className="chip-button" onClick={() => onBand(b)}>
            Show the {counts[b]} {BAND_NAMES[b].toLowerCase()}
          </button>
        ))}
        {wider && (
          <button type="button" className="chip-button" onClick={() => onFilters({ ...filters, km: wider })}>
            Widen to {wider} km
          </button>
        )}
        {filters.near && (
          <button
            type="button"
            className="chip-button"
            onClick={() => onFilters({ ...filters, near: undefined, lat: undefined, lon: undefined, km: undefined })}
          >
            Anywhere
          </button>
        )}
        {quietArrive && quietArrive !== filters.arrive && (
          <button
            type="button"
            className="chip-button"
            onClick={() => onFilters({ ...filters, arrive: quietArrive, depart: addDays(quietArrive, stay) })}
          >
            Try its quietest week: {dateRange(quietArrive, addDays(quietArrive, stay))}
          </button>
        )}
      </div>
    </div>
  )
}

// Trying again goes back to "Finding campgrounds…" (a query with no data is pending again).
function ExploreError({ error, onRetry }: { error: Error; onRetry: () => void }) {
  const errors = fieldErrors(error)
  return (
    <div role="alert" className="error">
      <p>{errors.length > 0 ? 'Check the dates:' : "The campgrounds didn't load."}</p>
      {errors.length > 0 ? (
        <ul>
          {errors.map((e) => (
            <li key={`${e.field}: ${e.message}`}>{e.message}</li>
          ))}
        </ul>
      ) : (
        <button type="button" className="chip-button" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  )
}
