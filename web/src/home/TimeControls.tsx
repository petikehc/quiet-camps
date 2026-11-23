import { useMemo } from 'react'
import { holidayOn, nightDate } from '../charts/dates'
import { formatNight, holidayName } from '../charts/scales'
import { peaks } from '../charts/strip'
import { YearStrip } from '../charts/YearStrip'
import { nightlySites, nightOffsets, type Trips } from './trips'

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
  const date = nightDate(trips.first_night, night)
  const holiday = holidayOn(trips.holidays, night)
  const said = (n: number) => {
    const h = holidayOn(trips.holidays, n)
    const on = formatNight(nightDate(trips.first_night, n))
    return `${on}${h ? `, ${holidayName(h.name)}` : ''}: ${totals[n].toLocaleString()} campsites arriving`
  }

  return (
    <div className="home-time">
      <div className="home-now-row">
        {/* Numbers that change four times a second: not live regions, or a screen reader
            would never stop. The strip's slider says where the year is when asked. */}
        <p className="home-now" aria-hidden="true">
          <span>
            {formatNight(date)}
            {holiday && <b> · {holidayName(holiday.name)}</b>}
          </span>
          <strong>{totals[night].toLocaleString()}</strong> campsites arriving
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

function shortDate(day: string): string {
  return new Date(`${day}T00:00:00Z`).toLocaleDateString('en-AU', {
    day: 'numeric',
    month: 'short',
    timeZone: 'UTC',
  })
}
