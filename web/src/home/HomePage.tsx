import { queryOptions, useQuery } from '@tanstack/react-query'
import { Link, useNavigate } from '@tanstack/react-router'
import { lazy, Suspense, useMemo, useRef, useState, type FormEvent } from 'react'
import { api } from '../api/client'
import { nightDate } from '../charts/dates'
import { unwrap } from '../api/errors'
import australia from './australia.json'
import { failedWords, filtersFrom, useAsk } from '../explore/ask'
import { monthBoard, monthOf, months, quietMask, usualNightly, type Count } from './quiet'
import { NightFigure, TimeControls } from './TimeControls'
import type { Seek } from './TripsScene'
import { busiestNight, nightOffsets, periodWords, project, type Trips } from './trips'

// three.js is most of a megabyte: the page shows the outline below until it arrives.
const TripsScene = lazy(() => import('./TripsScene'))

// The latest 12 months of history, whenever the page is opened: not last calendar year's.
const latestTrips = queryOptions({
  queryKey: ['trips', 'latest'],
  queryFn: ({ signal }) => unwrap(api.GET('/trips/latest', { signal })),
  staleTime: Infinity, // the API caches it for a day; within a visit it can't change
})

// Read once: the page doesn't restart its animation if the setting changes mid-visit.
const REDUCED_MOTION = window.matchMedia('(prefers-reduced-motion: reduce)').matches

export function HomePage() {
  const query = useQuery(latestTrips)
  const trips = query.data
  // The year's clock lives in the scene; the page hears each night, and asks for jumps.
  const [night, setNight] = useState(0)
  const [playing, setPlaying] = useState(!REDUCED_MOTION)
  const [seek, setSeek] = useState<Seek>()

  function jump(to: number) {
    setSeek((last) => ({ night: to, id: (last?.id ?? 0) + 1 }))
  }

  return (
    <article className="home">
      {/* The night stage: the words are HTML over the WebGL map, and come first so a screen
          reader and the tab order meet the headline before the controls. */}
      <section className="home-stage" aria-labelledby="home-title">
        <div className="home-left">
          <div className="home-intro">
            <h2 id="home-title">The map you need to beat the crowd.</h2>
            <p>
              Each line is a camping trip to a Queensland national park in the latest 12 months,
              from the camper's home postcode. Most end up in the same few places; the campgrounds in
              between stay quiet. Tell us where and when, and we'll find you one.
            </p>
            <HomeAsk />
          </div>
          {trips ? (
            <TimeControls
              trips={trips}
              night={night}
              playing={playing}
              onPlaying={setPlaying}
              onSeek={jump}
            />
          ) : query.isError ? (
            <div className="home-status" role="alert">
              <p>The year's camping data didn't load.</p>
              <button type="button" onClick={() => void query.refetch()} disabled={query.isFetching}>
                {query.isFetching ? 'Trying again…' : 'Try again'}
              </button>
            </div>
          ) : (
            <p className="home-status" role="status">
              Loading a year of camping…
            </p>
          )}
        </div>
        <div className="home-map">
          <Outline />
          {trips && <NightFigure trips={trips} night={night} />}
          {trips && <Live trips={trips} night={night} seek={seek} playing={playing} onNight={setNight} />}
        </div>
        {trips && <Board trips={trips} night={night} />}
      </section>
      <div className="wrap">{trips && <About trips={trips} />}</div>
    </article>
  )
}

// Asked with nothing typed, the box offers these: each one asks.
const EXAMPLES = ['Easter near Noosa', 'next long weekend from Brisbane', 'school holidays around Cairns']

// One question in plain words: /ask reads it, and the map opens on what it understood. If /ask
// can't be asked, it says so, and the map is a link away.
function HomeAsk() {
  const navigate = useNavigate()
  const input = useRef<HTMLInputElement>(null)
  const [text, setText] = useState('')
  const [note, setNote] = useState<string>()
  const [examples, setExamples] = useState(false)
  const ask = useAsk(
    (answer) => void navigate({ to: '/explore', search: filtersFrom(answer) }),
    (error) => setNote(failedWords(error)),
  )

  function submit(e: FormEvent) {
    e.preventDefault()
    if (text.trim().length >= 3) return ask.mutate(text.trim())
    setNote(undefined)
    setExamples(true)
    input.current?.focus()
  }

  function askExample(example: string) {
    setText(example)
    setExamples(false)
    ask.mutate(example)
  }

  return (
    <form className="home-ask" role="search" onSubmit={submit}>
      <label htmlFor="home-ask-text">Where and when?</label>
      <div className="home-ask-row">
        <input
          id="home-ask-text"
          ref={input}
          value={text}
          maxLength={200}
          placeholder="next weekend around the Sunshine Coast"
          onChange={(e) => setText(e.target.value)}
        />
        <button type="submit" className="cta" disabled={ask.isPending}>
          {ask.isPending ? 'Reading…' : 'Find quiet camps'} <Arrow />
        </button>
      </div>
      <p className="home-hint" aria-live="polite">
        {note ?? (examples && 'Type where and when, or try one of these:')}
      </p>
      {examples && (
        <div className="chips home-examples">
          {EXAMPLES.map((example) => (
            <button key={example} type="button" className="chip-button" onClick={() => askExample(example)}>
              {example}
            </button>
          ))}
        </div>
      )}
      <Link to="/explore" className="home-browse">
        Or browse the map
      </Link>
    </form>
  )
}

function Arrow() {
  return (
    <svg width="18" height="14" viewBox="0 0 18 14" aria-hidden="true">
      <path
        d="M1 7h15M10 1l6 6-6 6"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.25"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

type LiveProps = {
  trips: Trips
  night: number
  seek?: Seek
  playing: boolean
  onNight: (night: number) => void
}

// The map, once a year of trips has loaded.
function Live({ trips, night, seek, playing, onNight }: LiveProps) {
  const offsets = useMemo(() => nightOffsets(trips.per_night), [trips])
  // Motion reduced: no autoplay, and the busiest night as a still until Play.
  const [start] = useState(() => (REDUCED_MOTION ? busiestNight(trips, offsets) : 0))
  // The teal rings change once a month, not every night.
  const monthList = useMemo(() => months(trips), [trips])
  const nightly = useMemo(() => usualNightly(trips), [trips])
  const m = monthOf(monthList, night)
  const quiet = useMemo(
    () => quietMask(trips, offsets, nightly, monthList[m]),
    [trips, offsets, nightly, monthList, m],
  )

  return (
    <>
      <Suspense fallback={null}>
        <div className="home-canvas">
          <TripsScene
            trips={trips}
            startNight={start}
            seek={seek}
            playing={playing}
            drift={!REDUCED_MOTION}
            quiet={quiet}
            onNight={onNight}
          />
        </div>
      </Suspense>

    </>
  )
}

// This month's campgrounds well over and well under their usual month: beside the map on a
// wide screen, under the year strip on a phone. Against their own usual, so the same big
// beach campgrounds don't top it every month.
function Board({ trips, night }: { trips: Trips; night: number }) {
  const offsets = useMemo(() => nightOffsets(trips.per_night), [trips])
  const monthList = useMemo(() => months(trips), [trips])
  const nightly = useMemo(() => usualNightly(trips), [trips])
  const m = monthOf(monthList, night)
  const board = useMemo(
    () => monthBoard(trips, offsets, nightly, monthList[m]),
    [trips, offsets, nightly, monthList, m],
  )
  const firstDay = nightDate(trips.first_night, monthList[m].first)
  const month = new Date(`${firstDay}T00:00:00Z`).toLocaleDateString('en-AU', {
    month: 'long',
    timeZone: 'UTC',
  })
  const year = Number(firstDay.slice(0, 4)) // a name opens that campground's year at this month

  const rows = (counts: Count[]) => (
    <ol>
      {counts.map(({ campground, sites, usual }) => (
        <li key={campground}>
          <Link
            to="/campgrounds/$campgroundId"
            params={{ campgroundId: String(trips.campgrounds[campground].id) }}
            search={{ year }}
          >
            {trips.campgrounds[campground].name}
          </Link>
          <span>
            <b>{sites.toLocaleString()}</b> <small>· usually {usual.toLocaleString()}</small>
          </span>
        </li>
      ))}
    </ol>
  )

  // Keyed by month, so each month's lists fade in once. A real list a screen reader can read and
  // follow, but not a live region: it changes every 7 seconds while the year plays.
  return (
    <div className="home-board" aria-label={`The board for ${month}`} role="region">
      <div key={m}>
        <h3>
          <span className="key key-busy" /> Busier than usual in {month}
        </h3>
        {board.busier.length ? rows(board.busier) : <p>None well over their usual {month}.</p>}
        <h3>
          <span className="key key-quiet" /> Quiet in {month}
        </h3>
        {board.quiet.length ? (
          rows(board.quiet)
        ) : (
          <p>None: every regular campground had at least half its usual {month}.</p>
        )}
        <p>Campsites arriving in the month, and in an average month there.</p>
      </div>
    </div>
  )
}

// What the map shows, in words: for screen readers, and for anyone wondering.
function About({ trips }: { trips: Trips }) {
  const total = trips.sites.reduce((sum, s) => sum + s, 0)
  const { overseas, no_postcode, no_centroid } = trips.left_out
  return (
    <div className="home-about">
      <h2>Reading the map</h2>
      <p>
        Each line is a camping trip: campsites booked at a Queensland national park campground,
        flying from the camper's home postcode on the night they arrive. Brighter lines carry more
        campsites, and a campground glows as they land. {capitalised(periodWords(trips))},{' '}
        {total.toLocaleString()} campsites were booked from{' '}
        {trips.origins.length.toLocaleString()} postcodes at{' '}
        {trips.campgrounds.length.toLocaleString()} campgrounds. The year plays in about a minute
        and a half, then starts again.
      </p>
      <p>
        Teal rings mark campgrounds having a quiet month: open, but at half their usual month or
        less. Beside the map, the board names three of them each month, and three busier than
        their usual, with the campsites booked to arrive and the usual for that month; each name
        opens that campground's year.
      </p>
      <p className="muted small">
        Not drawn: {overseas.toLocaleString()} campsites booked from overseas, and{' '}
        {(no_postcode + no_centroid).toLocaleString()} with no postcode or a PO-box postcode. A
        postcode is placed at the centre of its ABS postal area (2021).
      </p>
    </div>
  )
}

function capitalised(words: string): string {
  return words.charAt(0).toUpperCase() + words.slice(1)
}

// The continent as plain SVG, drawn before three.js and the trips arrive.
const OUTLINE = (() => {
  const paths = australia.features.flatMap((state) =>
    state.geometry.coordinates.map(
      ([ring]) => 'M' + ring.map(([lon, lat]) => project(lon, lat).map((v) => v.toFixed(2)).join(',')).join('L') + 'Z',
    ),
  )
  return paths.join('')
})()

function Outline() {
  // The projection's units: x east from 134°E, z south from 28°S.
  return (
    <svg className="home-outline" viewBox="-19 -18 38 34" aria-hidden="true">
      <path d={OUTLINE} />
    </svg>
  )
}
