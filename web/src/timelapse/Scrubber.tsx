import { useMemo, type PointerEvent } from 'react'
import { formatNight, holidayName, niceTicks } from '../charts/scales'
import { holidayOn, nightDate, type Year } from './timelapse'

const WIDTH = 900
const HEIGHT = 140
const LEFT = 52 // y-axis ticks
const RIGHT = 12
const TOP = 10
const BOTTOM = 22 // month labels
const PLOT_W = WIDTH - LEFT - RIGHT
const PLOT_H = HEIGHT - TOP - BOTTOM
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

type Props = {
  year: Year
  totals: number[] // statewide campers per night
  night: number
  onSeek: (night: number) => void
}

// The whole year at once: campers statewide each night, holidays shaded, the playhead where
// the 3D view is. Dragging on it, or the slider under it, moves the time-lapse.
export function Scrubber({ year, totals, night, onSeek }: Props) {
  const last = year.nights - 1
  const ticks = niceTicks(Math.max(...totals), 2)
  const top = ticks.at(-1) ?? 1
  const x = (n: number) => LEFT + (n / Math.max(1, last)) * PLOT_W
  const y = (campers: number) => TOP + PLOT_H * (1 - campers / top)
  const line = totals.map((c, n) => `${n === 0 ? 'M' : 'L'}${x(n)},${y(c)}`).join('')

  function seek(event: PointerEvent<SVGRectElement>) {
    if (event.type === 'pointermove' && event.buttons !== 1) return
    const svg = event.currentTarget.ownerSVGElement?.getBoundingClientRect()
    if (!svg) return
    const viewX = ((event.clientX - svg.left) / svg.width) * WIDTH
    onSeek(Math.round(Math.min(1, Math.max(0, (viewX - LEFT) / PLOT_W)) * last))
  }

  const holiday = holidayOn(year.holidays, night)
  const date = nightDate(year.first_night, night)

  return (
    <div className="chart scrubber">
      <div className="chart-scroll">
        <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} style={{ maxWidth: WIDTH }} aria-hidden="true">
          {year.holidays.map((h) => (
            <rect
              key={h.night}
              className="holiday-band"
              x={x(h.night) - 1}
              y={TOP}
              width={Math.max(2, x(h.night + h.nights - 1) - x(h.night) + 2)}
              height={PLOT_H}
            />
          ))}
          {ticks.map((tick) => (
            <g key={tick}>
              <line className={tick === 0 ? 'baseline' : 'gridline'} x1={LEFT} x2={LEFT + PLOT_W} y1={y(tick)} y2={y(tick)} />
              <text className="axis-label" x={LEFT - 8} y={y(tick) + 4} textAnchor="end">
                {tick.toLocaleString()}
              </text>
            </g>
          ))}
          {MONTHS.map((label, month) => {
            const first = (Date.UTC(year.year, month, 1) - Date.UTC(year.year, 0, 1)) / 86_400_000
            if (first > last) return null
            return (
              <text key={label} className="axis-label" x={x(first)} y={HEIGHT - 6}>
                {label}
              </text>
            )
          })}
          <path className="line line-1" d={line} />
          <line className="playhead" x1={x(night)} x2={x(night)} y1={TOP - 4} y2={TOP + PLOT_H} />
          <rect className="hit-area" x={LEFT} y={0} width={PLOT_W} height={HEIGHT} onPointerDown={seek} onPointerMove={seek} />
        </svg>
      </div>
      <input
        type="range"
        className="scrubber-range"
        min={0}
        max={last}
        value={night}
        onChange={(e) => onSeek(Number(e.target.value))}
        aria-label="Night"
        aria-valuetext={`${formatNight(date)}${holiday ? `, ${holidayName(holiday.name)}` : ''}: ${totals[night].toLocaleString()} campers statewide`}
      />
      <ul className="legend">
        <li>
          <span className="line-key line-1" /> Campers statewide, each night
        </li>
        <li>
          <span className="swatch holiday-band" /> Public holidays and their long weekends
        </li>
      </ul>
      <BusiestNights year={year} totals={totals} />
    </div>
  )
}

function BusiestNights({ year, totals }: { year: Year; totals: number[] }) {
  const busiest = useMemo(
    () =>
      totals
        .map((campers, night) => ({ campers, night }))
        .sort((a, b) => b.campers - a.campers)
        .slice(0, 10),
    [totals],
  )
  return (
    <details>
      <summary>Show the year's ten busiest nights as a table</summary>
      <table className="data-table">
        <caption>Campers statewide, every campground together</caption>
        <thead>
          <tr>
            <th scope="col">Night</th>
            <th scope="col">Holiday</th>
            <th scope="col">Campers</th>
          </tr>
        </thead>
        <tbody>
          {busiest.map(({ campers, night }) => {
            const holiday = holidayOn(year.holidays, night)
            return (
              <tr key={night}>
                <td>{formatNight(nightDate(year.first_night, night))}</td>
                <td>{holiday ? holidayName(holiday.name) : ''}</td>
                <td>{campers.toLocaleString()}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </details>
  )
}
