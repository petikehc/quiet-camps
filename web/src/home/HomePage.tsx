import { queryOptions, useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { lazy, Suspense, useMemo, useState } from 'react'
import { api } from '../api/client'
import { unwrap } from '../api/errors'
import { formatNight } from '../charts/scales'
import { nightDate } from '../timelapse/timelapse'
import australia from './australia.json'
import { busiestNight, homeYear, nightOffsets, project, sitesOn, week, type Trips } from './trips'

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
      <div className="home-map">
        <Outline />
        {trips && <Live trips={trips} />}
        {query.isError && <p role="alert">{query.error.message}</p>}
      </div>
      <p className="home-cta">
        <Link to="/search" className="cta">
          Find a quiet campground →
        </Link>
      </p>
      {trips && <About trips={trips} />}
    </article>
  )
}

// The map, its numbers and its controls, once a year of trips has loaded.
function Live({ trips }: { trips: Trips }) {
  const offsets = useMemo(() => nightOffsets(trips.per_night), [trips])
  // Motion reduced: no autoplay, and the busiest night as a still until Play.
  const [start] = useState(() => (REDUCED_MOTION ? busiestNight(trips, offsets) : 0))
  const [night, setNight] = useState(start)
  const [playing, setPlaying] = useState(!REDUCED_MOTION)
  const now = useMemo(() => week(trips, offsets, night), [trips, offsets, night])

  return (
    <>
      <Suspense fallback={null}>
        <div className="home-canvas">
          <TripsScene
            trips={trips}
            startNight={start}
            playing={playing}
            drift={!REDUCED_MOTION}
            onNight={setNight}
          />
        </div>
      </Suspense>

      {/* Numbers that change four times a second: not live regions, or a screen reader
          would never stop. The summary below the map says it once. */}
      <div className="home-now" aria-hidden="true">
        <h2>Camping trips across Australia, {trips.year}</h2>
        <p className="home-date">{formatNight(nightDate(trips.first_night, night))}</p>
        <p className="home-hero">
          <strong>{sitesOn(trips, offsets, night).toLocaleString()}</strong> campsites arriving that night
        </p>
      </div>

      <div className="home-board" aria-hidden="true">
        <h3>Busiest this week</h3>
        <ol>
          {now.busiest.map(({ campground, sites }) => (
            <li key={campground}>
              <span>{trips.campgrounds[campground].name}</span>
              <span>{sites.toLocaleString()}</span>
            </li>
          ))}
        </ol>
        <p>
          From Queensland <strong>{Math.round(now.queensland * 100)}%</strong> · interstate{' '}
          <strong>{100 - Math.round(now.queensland * 100)}%</strong>
        </p>
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
      <p>
        Each line is a camping trip in {trips.year}: a site booked at a Queensland national park
        campground, flying from the camper's home postcode to the campground on the night they
        arrived. {total.toLocaleString()} campsites booked from{' '}
        {trips.origins.length.toLocaleString()} postcodes at{' '}
        {trips.campgrounds.length.toLocaleString()} campgrounds; the year plays in about a minute and
        a half, then starts again.
      </p>
      <p className="muted small">
        Not drawn: {overseas.toLocaleString()} campsites booked from overseas,{' '}
        {(no_postcode + no_centroid).toLocaleString()} with no postcode or a PO-box postcode. A
        postcode is placed at its postal area's centre. Boundaries and postal areas: ABS
        Australian Statistical Geography Standard 2021, © Commonwealth of Australia, CC BY 4.0.
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
