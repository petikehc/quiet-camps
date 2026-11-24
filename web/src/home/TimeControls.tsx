import { useMemo, useState } from 'react'
import { holidayOn, nightDate } from '../charts/dates'
import { formatNight, holidayName } from '../charts/scales'
import { peaks } from '../charts/strip'
import { YearStrip } from '../charts/YearStrip'
import { nightlySites, nightOffsets, swellByNight, type Trips } from './trips'
import { useEased } from './useEased'
import { useSoundScene } from '../sound/scene'

const NAMED = 3 // peaks named on the strip
const APART = 60 // nights between them, so their names don't collide

type Props = {
  trips: Trips
  night: number
  playing: boolean
  onPlaying: (playing: boolean) => void
  onSeek: (night: number) => void
}

// Where the year is: tonight's date and arrivals, Pause, and the whole year as a strip to drag.
export function TimeControls({ trips, night, playing, onPlaying, onSeek }: Props) {
  const totals = useMemo(() => nightlySites(trips, nightOffsets(trips.per_night)), [trips])
  const named = useMemo(
    () =>
      peaks(totals, NAMED, APART).map((n) => {
        const h = holidayOn(trips.holidays, n)
        return { night: n, text: h ? holidayName(h.name) : shortDate(nightDate(trips.first_night, n)) }
      }),
    [totals, trips],
  )
  // The night sounds (switched in the header) follow the stretch the year is playing through.
  const swell = useMemo(() => swellByNight(totals), [totals])
  useSoundScene(swell[night] ?? 0, playing)

  const said = (n: number) => {
    const h = holidayOn(trips.holidays, n)
    const on = formatNight(nightDate(trips.first_night, n))
    return `${on}${h ? `, ${holidayName(h.name)}` : ''}: ${totals[n].toLocaleString()} campsites booked from that night`
  }

  return (
    <div className="home-time">
      <div className="home-now-row">
        <p className="home-key">
          <span>
            <span className="key-trip" /> a trip, home to campground
          </span>{' '}
          <span>
            <span className="key-ring" /> a quiet month: half its usual or less
          </span>
        </p>
        {/* The label says what a press does; aria-pressed as well would announce "Play, pressed". */}
        <button type="button" className="home-play" onClick={() => onPlaying(!playing)}>
          {playing ? 'Pause' : 'Play'}
        </button>
      </div>
      <YearStrip
        firstNight={trips.first_night}
        values={totals}
        holidays={trips.holidays}
        night={night}
        onSeek={onSeek}
        labels={named}
        ariaLabel="Night of the year"
        valueText={said}
      />
    </div>
  )
}

// Tonight's date and arrivals, big over the map. Numbers that change four times a second: not a
// live region, or a screen reader would never stop; the strip's slider says it when asked.
export function NightFigure({ trips, night }: { trips: Trips; night: number }) {
  const totals = useMemo(() => nightlySites(trips, nightOffsets(trips.per_night)), [trips])
  const holiday = holidayOn(trips.holidays, night)
  const count = useEased(totals[night])
  // The holiday's name fades in while the year plays through it, and keeps its words while it
  // fades out again.
  const name = holiday && holidayName(holiday.name)
  const [lastName, setLastName] = useState(name)
  if (name && name !== lastName) setLastName(name)
  return (
    <p className="home-now" aria-hidden="true">
      <span className={name ? 'home-holiday on' : 'home-holiday'}>{lastName}</span>
      <span>{formatNight(nightDate(trips.first_night, night))}</span>
      <strong>{Math.round(count).toLocaleString()}</strong> campsites booked from that night
    </p>
  )
}

function shortDate(day: string): string {
  return new Date(`${day}T00:00:00Z`).toLocaleDateString('en-AU', {
    day: 'numeric',
    month: 'short',
    timeZone: 'UTC',
  })
}
