import { useMemo } from 'react'
import { formatNight, holidayName } from '../charts/scales'
import { holidayOn, nightDate } from '../charts/dates'
import { nightlySites, nightOffsets, peaks, type Trips } from './trips'

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
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
  const named = useMemo(() => peaks(totals, NAMED, APART), [totals])
  const date = nightDate(trips.first_night, night)
  const holiday = holidayOn(trips.holidays, night)

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
      <YearStrip trips={trips} totals={totals} named={named} night={night} onSeek={onSeek} />
    </div>
  )
}

const W = 1000 // the strip's drawing units; it stretches to its box
const H = 100

type StripProps = {
  trips: Trips
  totals: number[]
  named: number[]
  night: number
  onSeek: (night: number) => void
}

// The year's arrivals as one shape, holidays shaded and the peaks named. The slider over it is
// the playhead: drag it, or use the arrow keys.
function YearStrip({ trips, totals, named, night, onSeek }: StripProps) {
  const last = trips.nights - 1
  const shape = useMemo(() => {
    const top = Math.max(1, ...totals)
    const x = (n: number) => (n / last) * W
    const y = (sites: number) => H - (sites / top) * H * 0.92
    const line = totals.map((s, n) => `${n ? 'L' : 'M'}${x(n).toFixed(1)},${y(s).toFixed(1)}`).join('')
    return { line, area: `${line}L${W},${H}L0,${H}Z`, x }
  }, [totals, last])
  // Positions in the strip's box, matching the slider's thumb centre: see .year-strip in CSS.
  const at = (n: number) => `calc(var(--thumb) / 2 + ${n / last} * (100% - var(--thumb)))`
  const date = nightDate(trips.first_night, night)
  const holiday = holidayOn(trips.holidays, night)

  return (
    <div className="year-strip">
      <ol className="year-peaks" aria-hidden="true">
        {named.map((n) => {
          const h = holidayOn(trips.holidays, n)
          const label = h
            ? holidayName(h.name)
            : new Date(`${nightDate(trips.first_night, n)}T00:00:00Z`).toLocaleDateString('en-AU', {
                day: 'numeric',
                month: 'short',
                timeZone: 'UTC',
              })
          return (
            <li key={n} style={{ left: at(n) }}>
              {label}
            </li>
          )
        })}
      </ol>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" aria-hidden="true">
        {trips.holidays.map((h) => (
          <rect
            key={h.night}
            className="year-holiday"
            x={shape.x(h.night)}
            width={Math.max(3, shape.x(h.night + h.nights) - shape.x(h.night))}
            y={0}
            height={H}
          />
        ))}
        <path className="year-area" d={shape.area} />
        <path className="year-line" d={shape.line} vectorEffect="non-scaling-stroke" />
      </svg>
      <input
        type="range"
        min={0}
        max={last}
        value={night}
        onChange={(e) => onSeek(Number(e.target.value))}
        aria-label="Night of the year"
        aria-valuetext={`${formatNight(date)}${holiday ? `, ${holidayName(holiday.name)}` : ''}: ${totals[night].toLocaleString()} campsites arriving`}
      />
      <ol className="year-months" aria-hidden="true">
        {MONTHS.map((month, m) => {
          const first = (Date.UTC(trips.year, m, 1) - Date.UTC(trips.year, 0, 1)) / 86_400_000
          return first > last ? null : (
            <li key={month} style={{ left: at(first) }}>
              {month}
            </li>
          )
        })}
      </ol>
    </div>
  )
}
