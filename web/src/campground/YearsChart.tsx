import { useRef, useState, type PointerEvent } from 'react'
import type { components } from '../api/schema'
import { pointerIn, type TooltipAt } from '../charts/pointer'
import { niceTicks } from '../charts/scales'
import { Tooltip } from '../charts/Tooltip'

type Year = components['schemas']['YearSitesOut']

const WIDTH = 900
const HEIGHT = 260
const LEFT = 44 // y-axis ticks
const RIGHT = 44 // end labels
const TOP = 12
const BOTTOM = 24 // month labels
const PLOT_W = WIDTH - LEFT - RIGHT
const PLOT_H = HEIGHT - TOP - BOTTOM
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

const x = (month: number) => LEFT + ((month - 1) / 11) * PLOT_W

// Sites booked per month, a line per year. Emphasis instead of a colour per year: the latest
// year and the one before carry colour, earlier years are thin grey context.
export function YearsChart({ years }: { years: Year[] }) {
  const box = useRef<HTMLDivElement>(null)
  const [hover, setHover] = useState<{ month: number; at: TooltipAt }>()
  const latest = years.at(-1)
  const previous = years.at(-2)
  const earlier = years.slice(0, -2)
  if (!latest) return <p>No bookings yet.</p>

  const ticks = niceTicks(Math.max(...years.flatMap((y) => y.months.map((m) => m.sites ?? 0))))
  const top = ticks.at(-1) ?? 1
  const y = (sites: number) => TOP + PLOT_H * (1 - sites / top)

  function path(year: Year): string {
    // A null month breaks the line: M starts a new segment after a gap.
    let d = ''
    let drawing = false
    for (const { month, sites } of year.months) {
      if (sites === null) {
        drawing = false
        continue
      }
      d += `${drawing ? 'L' : 'M'}${x(month)},${y(sites)}`
      drawing = true
    }
    return d
  }

  function lastPoint(year: Year) {
    const last = year.months.findLast((m) => m.sites !== null)
    return last && { x: x(last.month), y: y(last.sites ?? 0) }
  }

  function onPointerMove(event: PointerEvent<SVGRectElement>) {
    const svgBox = event.currentTarget.ownerSVGElement?.getBoundingClientRect()
    if (!svgBox) return
    const viewX = ((event.clientX - svgBox.left) / svgBox.width) * WIDTH
    const month = Math.min(12, Math.max(1, Math.round(((viewX - LEFT) / PLOT_W) * 11) + 1))
    setHover({ month, at: pointerIn(event, box.current) })
  }

  const emphasised = [
    { year: latest, className: 'line-1' },
    ...(previous ? [{ year: previous, className: 'line-2' }] : []),
  ].reverse() // draw the latest year last, on top

  return (
    <div className="chart" ref={box}>
      <ul className="legend">
        <li>
          <span className="line-key line-1" />
          {latest.year}
        </li>
        {previous && (
          <li>
            <span className="line-key line-2" />
            {previous.year}
          </li>
        )}
        {earlier.length > 0 && (
          <li>
            <span className="line-key line-muted" />
            {earlier[0].year}–{earlier.at(-1)?.year}
          </li>
        )}
      </ul>
      <div className="chart-scroll">
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          style={{ maxWidth: WIDTH }} // never scaled up, so its 11px text stays 11px
          role="img"
          aria-label="Sites booked each month, one line per year. The table below has every value."
        >
          {ticks.map((tick) => (
            <g key={tick}>
              <line className={tick === 0 ? 'baseline' : 'gridline'} x1={LEFT} x2={LEFT + PLOT_W} y1={y(tick)} y2={y(tick)} />
              <text className="axis-label" x={LEFT - 8} y={y(tick) + 4} textAnchor="end">
                {tick.toLocaleString()}
              </text>
            </g>
          ))}
          {MONTHS.map((label, i) => (
            <text key={label} className="axis-label" x={x(i + 1)} y={HEIGHT - 6} textAnchor="middle">
              {label}
            </text>
          ))}
          {hover && <line className="crosshair" x1={x(hover.month)} x2={x(hover.month)} y1={TOP} y2={TOP + PLOT_H} />}
          {earlier.map((year) => (
            <path key={year.year} className="line line-muted" d={path(year)} />
          ))}
          {emphasised.map(({ year, className }) => {
            const end = lastPoint(year)
            return (
              <g key={year.year}>
                <path className={`line ${className}`} d={path(year)} />
                {end && (
                  <>
                    <circle className={`end-dot ${className}`} cx={end.x} cy={end.y} r={4} />
                    <text className="end-label" x={end.x + 8} y={end.y + 4}>
                      {year.year}
                    </text>
                  </>
                )}
              </g>
            )
          })}
          <rect
            className="hit-area"
            x={LEFT}
            y={TOP}
            width={PLOT_W}
            height={PLOT_H}
            onPointerMove={onPointerMove}
            onPointerLeave={() => setHover(undefined)}
          />
        </svg>
      </div>
      {hover && (
        <Tooltip at={hover.at}>
          <MonthDetails month={hover.month} latest={latest} previous={previous} earlier={earlier} />
        </Tooltip>
      )}
      <details>
        <summary>Show every year as a table</summary>
        <table className="data-table">
          <thead>
            <tr>
              <th scope="col">Year</th>
              {MONTHS.map((m) => (
                <th key={m} scope="col">
                  {m}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[...years].reverse().map((year) => (
              <tr key={year.year}>
                <th scope="row">{year.year}</th>
                {year.months.map((m) => (
                  <td key={m.month}>{m.sites ?? '–'}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  )
}

function MonthDetails(props: { month: number; latest: Year; previous?: Year; earlier: Year[] }) {
  const sites = (year: Year) => year.months[props.month - 1]?.sites
  const known = props.earlier.map(sites).filter((s) => s !== null && s !== undefined)
  const row = (year: Year, className: string) => (
    <div>
      <span className={`line-key ${className}`} /> <strong>{sites(year) ?? 'not known'}</strong> {year.year}
    </div>
  )
  return (
    <>
      <div>{MONTHS[props.month - 1]}, sites booked</div>
      {row(props.latest, 'line-1')}
      {props.previous && row(props.previous, 'line-2')}
      {known.length > 0 && (
        <div>
          <span className="line-key line-muted" />{' '}
          <strong>
            {Math.min(...known)}–{Math.max(...known)}
          </strong>{' '}
          earlier years
        </div>
      )}
    </>
  )
}
