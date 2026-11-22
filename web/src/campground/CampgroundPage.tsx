import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { getRouteApi, Link } from '@tanstack/react-router'
import { formatNight } from '../charts/scales'
import { Calendar } from './Calendar'
import { LeadTimeTable } from './LeadTime'
import { calendarQuery, campgroundQuery, leadTimeQuery, yearsQuery } from './queries'
import { FIRST_YEAR, lastYear } from './year'
import { YearsChart } from './YearsChart'

const route = getRouteApi('/campgrounds/$campgroundId')

export function CampgroundPage() {
  const id = Number(route.useParams().campgroundId)
  if (!Number.isSafeInteger(id) || id < 1) return <p role="alert">There's no campground at this address.</p>
  return <Campground id={id} />
}

function Campground({ id }: { id: number }) {
  const { year } = route.useSearch()
  const campground = useQuery(campgroundQuery(id))
  // The previous year stays on screen, faded, while the next one loads: no layout jump.
  const calendar = useQuery({ ...calendarQuery(id, year), placeholderData: keepPreviousData })
  const leadTime = useQuery(leadTimeQuery(id))
  const years = useQuery(yearsQuery(id))

  if (campground.isPending) return <p role="status">Loading…</p>
  if (campground.isError) return <p role="alert">{campground.error.message}</p>
  const { name, park_name, active, last_night } = campground.data

  return (
    <article className="campground">
      <h2>{name}</h2>
      <p className="muted">
        <Link to="/" search={{ park: park_name }}>
          {park_name}
        </Link>
        {!active && last_night && <> · No bookings since {formatNight(last_night)}</>}
      </p>

      <section>
        <h3>When it's busy</h3>
        <nav className="year-nav" aria-label="Calendar year">
          <YearLink year={year - 1} label="‹ Earlier" />
          <strong>{year}</strong>
          <YearLink year={year + 1} label="Later ›" />
        </nav>
        {calendar.isError && <p role="alert">{calendar.error.message}</p>}
        {calendar.data && (
          <div className={calendar.isPlaceholderData ? 'refetching' : undefined}>
            <Calendar name={name} nights={calendar.data.nights} />
          </div>
        )}
      </section>

      <section>
        <h3>How far ahead it's booked</h3>
        {leadTime.isError && <p role="alert">{leadTime.error.message}</p>}
        {leadTime.data && <LeadTimeTable leadTime={leadTime.data} />}
      </section>

      <section>
        <h3>Year on year</h3>
        {years.isError && <p role="alert">{years.error.message}</p>}
        {years.data && <YearsChart years={years.data.years} />}
      </section>
    </article>
  )
}

function YearLink({ year, label }: { year: number; label: string }) {
  if (year < FIRST_YEAR || year > lastYear()) return <span className="muted">{label}</span>
  return (
    <Link from="/campgrounds/$campgroundId" to="." search={{ year }}>
      {label}
    </Link>
  )
}
