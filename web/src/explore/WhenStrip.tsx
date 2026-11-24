import { useMemo } from 'react'
import { addDays } from './filters'
import { holidayOn, nightDate } from '../charts/dates'
import { formatNight, holidayName } from '../charts/scales'
import { peaks } from '../charts/strip'
import { YearStrip } from '../charts/YearStrip'
import { nightsBetween, quietestWeek, type ComingYear } from './comingYear'

type Props = {
  coming: ComingYear
  arrive: string
  depart: string
  near: string | undefined
  onDates: (arrive: string, depart: string) => void
}

// When it's quiet around here: the coming year for the campgrounds asked about, the busiest
// moments named and the quietest week pointed at. Dragging moves your dates, same length.
export function WhenStrip({ coming, arrive, depart, near, onDates }: Props) {
  const { firstNight, values, holidays, schoolHolidays } = coming
  const from = nightsBetween(firstNight, arrive)
  const to = nightsBetween(firstNight, depart)
  const labels = useMemo(() => {
    const named = peaks(values, 3, 60).map((n) => {
      const h = holidayOn(holidays, n)
      return { night: n, text: h ? holidayName(h.name) : shortDate(nightDate(firstNight, n)) }
    })
    const quiet = quietestWeek(values)
    const clear = quiet !== undefined && named.every((l) => Math.abs(l.night - quiet) > 40)
    return clear ? [...named, { night: quiet + 3, text: 'Quietest week' }] : named
  }, [values, holidays, firstNight])

  const said = (n: number) => {
    const h = holidayOn(holidays, n)
    const school = holidayOn(schoolHolidays, n)
    const v = values[n]
    const how = v === null ? 'usually closed' : `usually ${Math.round(v * 100)}% as busy as their busy nights`
    const names = [h && holidayName(h.name), school && 'school holidays'].filter(Boolean)
    return `${formatNight(nightDate(firstNight, n))}${names.length ? `, ${names.join(', ')}` : ''}: ${how}`
  }

  return (
    <section className="explore-when" aria-label="The coming year">
      <h2>
        {near ? `Around ${near}` : 'Across Queensland'}: the coming year{' '}
        <span>Drag to move your dates</span>
      </h2>
      <YearStrip
        firstNight={firstNight}
        values={values}
        holidays={holidays}
        schoolHolidays={schoolHolidays}
        night={Math.min(Math.max(from, 0), values.length - 1)}
        onSeek={(n) => {
          const arriving = nightDate(firstNight, n)
          onDates(arriving, addDays(arriving, Math.max(1, to - from)))
        }}
        labels={labels}
        stay={{ from, to }}
        ariaLabel="Arrival night"
        valueText={said}
      />
      <ul className="legend when-key" aria-label="Shaded on the strip">
        <li>
          <span className="swatch year-school" /> Queensland school holidays
        </li>
        <li>
          <span className="swatch year-holiday" /> Public holidays and long weekends
        </li>
        <li>
          <span className="swatch year-stay" /> Your nights
        </li>
      </ul>
    </section>
  )
}

// A busy night that isn't a holiday is named by its date: "Sat 15 May".
function shortDate(night: string): string {
  return new Date(`${night}T00:00:00Z`).toLocaleDateString('en-AU', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    timeZone: 'UTC',
  })
}
