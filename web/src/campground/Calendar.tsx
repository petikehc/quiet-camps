import { useRef, useState } from 'react'
import type { components } from '../api/schema'
import { pointerIn, type TooltipAt } from '../charts/pointer'
import { calendarCell, formatNight, HEAT_LABELS, heatBin, holidayName } from '../charts/scales'
import { Tooltip } from '../charts/Tooltip'

type Night = components['schemas']['CalendarNightOut']

const STEP = 16 // a 14px cell and the 2px surface gap that separates it from the next
const CELL = 14
const LEFT = 30 // weekday labels
const TOP = 18 // month labels
const COLUMNS = 54 // a leap year starting on a Sunday spans 54 weeks
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

const percent = (share: number) => `${Math.round(share * 100)}%`

// How busy each night of a year usually is, as a GitHub-style grid: a column per week.
export function Calendar({ name, nights }: { name: string; nights: Night[] }) {
  const box = useRef<HTMLDivElement>(null)
  const [hover, setHover] = useState<{ night: Night; at: TooltipAt }>()
  const year = nights[0]?.night.slice(0, 4)

  return (
    <div className="chart" ref={box}>
      <div className="chart-scroll">
        <svg
          viewBox={`0 0 ${LEFT + COLUMNS * STEP} ${TOP + 7 * STEP}`}
          style={{ maxWidth: LEFT + COLUMNS * STEP }} // never scaled up, so its 11px text stays 11px
          role="img"
          aria-label={`How busy ${name} usually is on each night of ${year}. The table below has every night.`}
          onPointerLeave={() => setHover(undefined)}
        >
          {MONTHS.map((month, i) => (
            <text key={month} className="axis-label" x={LEFT + calendarCell(`${year}-${String(i + 1).padStart(2, '0')}-01`).column * STEP} y={12}>
              {month}
            </text>
          ))}
          {['Mon', 'Wed', 'Fri'].map((day, i) => (
            <text key={day} className="axis-label" x={0} y={TOP + i * 2 * STEP + 11}>
              {day}
            </text>
          ))}
          {nights.map((night) => {
            const { column, row } = calendarCell(night.night)
            const bin = night.busyness === null ? undefined : heatBin(night.busyness)
            const x = LEFT + column * STEP
            const y = TOP + row * STEP
            return (
              <g key={night.night} onPointerMove={(e) => setHover({ night, at: pointerIn(e, box.current) })}>
                <rect
                  x={x}
                  y={y}
                  width={CELL}
                  height={CELL}
                  rx={2}
                  fill={bin === undefined ? 'var(--grid)' : `var(--heat-${bin})`}
                  className={hover?.night === night ? 'hovered' : undefined}
                />
                {night.holiday && (
                  <circle
                    cx={x + CELL / 2}
                    cy={y + CELL / 2}
                    r={2.5}
                    fill={bin === undefined ? 'var(--text)' : `var(--heat-ink-${bin})`}
                  />
                )}
              </g>
            )
          })}
        </svg>
      </div>
      {hover && (
        <Tooltip at={hover.at}>
          <NightDetails night={hover.night} />
        </Tooltip>
      )}
      <HeatLegend />
      <details>
        <summary>Show every night as a table</summary>
        <table className="data-table">
          <thead>
            <tr>
              <th scope="col">Night</th>
              <th scope="col">Holiday</th>
              <th scope="col">Usually</th>
              <th scope="col">Typical sites</th>
              <th scope="col">Booked sites</th>
            </tr>
          </thead>
          <tbody>
            {nights.map((night) => (
              <tr key={night.night}>
                <td>{formatNight(night.night)}</td>
                <td>{night.holiday && holidayName(night.holiday)}</td>
                <td>{night.busyness === null ? '–' : percent(night.busyness)}</td>
                <td>{night.typical_sites === null ? '–' : Math.round(night.typical_sites)}</td>
                <td>{night.sites ?? '–'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  )
}

function NightDetails({ night }: { night: Night }) {
  return (
    <>
      <strong>{formatNight(night.night)}</strong>
      {night.holiday && <div>{holidayName(night.holiday)}</div>}
      <div>
        {night.busyness === null || night.typical_sites === null
          ? 'No typical night: usually closed, or too little history'
          : `Usually ${percent(night.busyness)} busy, ${Math.round(night.typical_sites)} sites`}
      </div>
      <div>{night.sites === null ? 'Booked: not known yet' : `Booked: ${night.sites} sites`}</div>
    </>
  )
}

export function HeatLegend() {
  return (
    <ul className="legend">
      {HEAT_LABELS.map((label, bin) => (
        <li key={label}>
          <span className="swatch" style={{ background: `var(--heat-${bin})` }} />
          {label}
        </li>
      ))}
      <li>
        <span className="swatch" style={{ background: 'var(--grid)' }} />
        No typical night
      </li>
      <li>
        <span className="holiday-key" />
        Holiday
      </li>
    </ul>
  )
}
