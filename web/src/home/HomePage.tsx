import { queryOptions, useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { lazy, Suspense, useMemo, useState } from 'react'
import { api } from '../api/client'
import { unwrap } from '../api/errors'
import { formatNight } from '../charts/scales'
import { nightDate } from '../timelapse/timelapse'
import australia from './australia.json'
import { quietMask, usualWeekly, weekBoard, weekOf } from './quiet'
import { busiestNight, homeYear, nightOffsets, project, sitesOn, type Trips } from './trips'

// three.js is most of a megabyte: the page shows the outline below until it arrives.
const TripsScene = lazy(() => import('./TripsScene'))

const YEAR = homeYear()

const tripsQuery = (year: number) =>
  queryOptions({
    queryKey: ['trips', year],
    queryFn: ({ signal }) => unwrap(api.GET('/trips/{year}', { params: { path: { year } }, signal })),
    staleTime: Infinity, // the API caches a year for a day; within a visit it can't change
  })

// Read once: the page doesn't restart its animation if the setting changes mid-visit.
const REDUCED_MOTION = window.matchMedia('(prefers-reduced-motion: reduce)').matches

export function HomePage() {
  const query = useQuery(tripsQuery(YEAR))
  const trips = query.data

  return (
    <article className="home">
      {/* The night stage: the words are HTML over the WebGL map, and come first so a screen
          reader and the tab order meet the headline before the controls. */}
      <section className="home-stage" aria-labelledby="home-title">
        <div className="home-intro">
          <h2 id="home-title">A year of Queensland camping.</h2>
          <p>
            Each line is a camping trip in Queensland's national parks in {YEAR}, from the camper's
            home postcode. Watch where everyone went, and the campgrounds they left quiet.
          </p>
          <Link to="/search" className="cta">
            Find a quiet campground <Arrow />
          </Link>
        </div>
        <div className="home-map">
          <Outline />
          {trips && <Live trips={trips} />}
          {query.isError && <p role="alert">{query.error.message}</p>}
        </div>
      </section>
      <div className="wrap">{trips && <About trips={trips} />}</div>
    </article>
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

// The map, its numbers and its controls, once a year of trips has loaded.
function Live({ trips }: { trips: Trips }) {
  const offsets = useMemo(() => nightOffsets(trips.per_night), [trips])
  // Motion reduced: no autoplay, and the busiest night as a still until Play.
  const [start] = useState(() => (REDUCED_MOTION ? busiestNight(trips, offsets) : 0))
  const [night, setNight] = useState(start)
  const [playing, setPlaying] = useState(!REDUCED_MOTION)
  // The board and the teal points change once a week, not every night.
  const usual = useMemo(() => usualWeekly(trips), [trips])
  const w = weekOf(night, trips.nights)
  const board = useMemo(() => weekBoard(trips, offsets, usual, w), [trips, offsets, usual, w])
  const quiet = useMemo(() => quietMask(trips, offsets, usual, w), [trips, offsets, usual, w])

  return (
    <>
      <Suspense fallback={null}>
        <div className="home-canvas">
          <TripsScene
            trips={trips}
            startNight={start}
            playing={playing}
            drift={!REDUCED_MOTION}
            quiet={quiet}
            onNight={setNight}
          />
        </div>
      </Suspense>

      {/* Numbers that change four times a second: not live regions, or a screen reader
          would never stop. The summary below the map says it once. */}
      <p className="home-now" aria-hidden="true">
        <span>{formatNight(nightDate(trips.first_night, night))}</span>
        <strong>{sitesOn(trips, offsets, night).toLocaleString()}</strong> campsites arriving
      </p>

      {/* Keyed by week, so each week's lists fade in once rather than flickering. */}
      <div className="home-board" aria-hidden="true">
        <div key={w}>
          <h3>
            <span className="key key-busy" /> Busiest this week
          </h3>
          <ol>
            {board.busy.map(({ campground, sites }) => (
              <li key={campground}>
                <span>{trips.campgrounds[campground].name}</span>
                <span>{sites.toLocaleString()}</span>
              </li>
            ))}
          </ol>
          <h3>
            <span className="key key-quiet" /> Quiet this week
          </h3>
          {board.quiet.length ? (
            <ol>
              {board.quiet.map(({ campground, sites, usual }) => (
                <li key={campground}>
                  <span>{trips.campgrounds[campground].name}</span>
                  <span>
                    {sites.toLocaleString()} <small>of {usual.toLocaleString()}</small>
                  </span>
                </li>
              ))}
            </ol>
          ) : (
            <p>None: every regular campground had at least half its usual week.</p>
          )}
          <p>Campsites arriving this week, and in a usual week there.</p>
        </div>
      </div>

      {/* The label says what a press does; aria-pressed as well would announce "Play, pressed". */}
      <button type="button" className="home-play" onClick={() => setPlaying(!playing)}>
        {playing ? 'Pause' : 'Play'}
      </button>
    </>
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
        campsites, and a campground glows as they land. In {trips.year},{' '}
        {total.toLocaleString()} campsites were booked from{' '}
        {trips.origins.length.toLocaleString()} postcodes at{' '}
        {trips.campgrounds.length.toLocaleString()} campgrounds. The year plays in about a minute
        and a half, then starts again.
      </p>
      <p className="muted small">
        Not drawn: {overseas.toLocaleString()} campsites booked from overseas, and{' '}
        {(no_postcode + no_centroid).toLocaleString()} with no postcode or a PO-box postcode. A
        postcode is placed at the centre of its ABS postal area (2021).
      </p>
    </div>
  )
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
