import { keepPreviousData, queryOptions, useQuery } from '@tanstack/react-query'
import { getRouteApi } from '@tanstack/react-router'
import { lazy, Suspense, useMemo, useRef, useState } from 'react'
import { api } from '../api/client'
import { unwrap } from '../api/errors'
import { HeatKeys } from '../charts/HeatKeys'
import { formatNight, holidayName } from '../charts/scales'
import type { TooltipAt } from '../charts/pointer'
import { Tooltip } from '../charts/Tooltip'
import type { Hover } from './Scene'
import { Scrubber } from './Scrubber'
import { holidayOn, nightDate, peaks, statewide, timelapseYears } from './timelapse'

// three.js is most of a megabyte: only this page loads it.
const Scene = lazy(() => import('./Scene'))

const route = getRouteApi('/timelapse')

const yearQuery = (year: number) =>
  queryOptions({
    queryKey: ['year', year],
    queryFn: ({ signal }) => unwrap(api.GET('/year/{year}', { params: { path: { year } }, signal })),
    staleTime: Infinity, // the API caches a year for a day; within a visit it can't change
  })

const YEARS = timelapseYears()

const SPEEDS = [
  { nights: 7, label: 'A week a second' },
  { nights: 14, label: 'Two weeks a second' },
  { nights: 30, label: 'A month a second' },
]

export function TimelapsePage() {
  const { year } = route.useSearch()
  const navigate = route.useNavigate()
  // The previous year stays on screen while the next loads, so the canvas isn't rebuilt.
  const query = useQuery({ ...yearQuery(year), placeholderData: keepPreviousData })
  const [seekTo, setSeekTo] = useState({ night: 0 }) // a new object each time, so the same night again still seeks
  const [night, setNight] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(SPEEDS[0].nights)
  const [hover, setHover] = useState<{ row: number; at: TooltipAt }>()
  const box = useRef<HTMLDivElement>(null)

  const data = query.data
  const totals = useMemo(() => (data ? statewide(data) : []), [data])
  const peak = useMemo(() => (data ? peaks(data) : []), [data])

  function seek(to: number) {
    setSeekTo({ night: to })
    setNight(to)
  }

  function onHover(found: Hover | undefined) {
    const at = box.current?.getBoundingClientRect()
    setHover(found && at && { row: found.row, at: { x: found.clientX - at.left, y: found.clientY - at.top } })
  }

  function play() {
    if (data && night >= data.nights - 1) seek(0) // at the end: start again
    setPlaying(!playing)
  }

  if (query.isError) return <p role="alert">{query.error.message}</p>

  const shown = data && Math.min(night, data.nights - 1)
  const holiday = data && shown !== undefined ? holidayOn(data.holidays, shown) : undefined
  const unlocated = data?.campgrounds.filter((c) => c.lat === null).length ?? 0

  return (
    <article className="timelapse">
      <h2>A year of camping, night by night</h2>
      <p className="muted">
        Each column is a campground, as tall as its campers that night. Its colour is how busy it
        is against its own busiest night of the year. Drag to turn the state; scroll to zoom.
      </p>

      <div className="timelapse-controls">
        <label>
          Year{' '}
          <select
            value={year}
            onChange={(e) => {
              seek(0)
              void navigate({ search: { year: Number(e.target.value) } })
            }}
          >
            {YEARS.map((y) => (
              <option key={y}>{y}</option>
            ))}
          </select>
        </label>
        <button type="button" onClick={play} disabled={!data} aria-pressed={playing}>
          {playing ? 'Pause' : 'Play'}
        </button>
        <label>
          Speed{' '}
          <select value={speed} onChange={(e) => setSpeed(Number(e.target.value))}>
            {SPEEDS.map((s) => (
              <option key={s.nights} value={s.nights}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <p className="timelapse-date" aria-live="off">
        {data && shown !== undefined ? (
          <>
            <strong>{formatNight(nightDate(data.first_night, shown))}</strong>
            {holiday && <span className="holiday-name"> {holidayName(holiday.name)}</span>}
            <span className="muted"> · {totals[shown].toLocaleString()} campers statewide</span>
          </>
        ) : (
          <span role="status">Loading {year}…</span>
        )}
      </p>

      <div className={`timelapse-canvas${query.isPlaceholderData ? ' refetching' : ''}`} ref={box}>
        <Suspense fallback={null}>
          {data && (
            <Scene
              year={data}
              seekTo={seekTo}
              playing={playing}
              speed={speed}
              onNight={setNight}
              onEnd={() => setPlaying(false)}
              onHover={onHover}
            />
          )}
        </Suspense>
        {data && hover && shown !== undefined && (
          <Tooltip at={hover.at}>
            <strong>{data.campgrounds[hover.row].name}</strong>
            <div>{data.values[hover.row * data.nights + shown].toLocaleString()} campers tonight</div>
            <div className="muted">Busiest night this year: {peak[hover.row].toLocaleString()}</div>
          </Tooltip>
        )}
      </div>
      <ul className="legend">
        <HeatKeys />
        {data && <li>Tallest column: {Math.max(...peak).toLocaleString()} campers</li>}
      </ul>
      {unlocated > 0 && (
        <p className="muted small">
          {unlocated} campgrounds aren't located yet: they have no column, but count in the totals.
        </p>
      )}

      {data && shown !== undefined && <Scrubber year={data} totals={totals} night={shown} onSeek={seek} />}
      <p className="muted small">
        Outline: ABS Australian Statistical Geography Standard, © Commonwealth of Australia, CC BY 4.0.
      </p>
    </article>
  )
}
