import type { Holiday } from '../charts/dates'
import { holidayName } from '../charts/scales'
import { bookBy } from './bookBy'
import { useLeadTime } from './queries'

type Props = {
  campgroundId: number
  arrive: string
  holiday: Holiday | undefined // the holiday the arrival falls in, if any
  today: string
}

function ahead(weeks: number): string {
  if (weeks >= 52) return 'a year or more'
  if (weeks >= 8) return `about ${Math.round(weeks / 4.35)} months`
  if (weeks >= 1.5) return `about ${Math.round(weeks)} weeks`
  return 'about a week'
}

function day(date: string, today: string): string {
  return new Date(`${date}T00:00:00Z`).toLocaleDateString('en-AU', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    ...(date.slice(0, 4) === today.slice(0, 4) ? {} : { year: 'numeric' }),
    timeZone: 'UTC',
  })
}

// When people book this campground for nights like these, from its past bookings: how much
// time there is. Past bookings, not live availability: it never says a site is free.
export function BookingHint({ campgroundId, arrive, holiday, today }: Props) {
  const lead = useLeadTime(campgroundId, true)
  if (!lead.data) return lead.isPending ? <p className="muted">Looking at how far ahead it's booked…</p> : null

  const hint = bookBy(lead.data, arrive, holiday)
  if (!hint) return <p className="muted">Too few past bookings to say how far ahead people book.</p>
  const kind = hint.group === 'weekend' || hint.group === 'weeknight' ? hint.group : holidayName(hint.group)
  return (
    <div className="book-by">
      {hint.weeks < 1 ? (
        <p>Most of its {kind} bookings are made in the last week.</p>
      ) : hint.date > today ? (
        <p>
          Half its {kind} bookings are made {ahead(hint.weeks)} ahead: for these nights,{' '}
          <strong>book by {day(hint.date, today)}</strong>.
        </p>
      ) : (
        <p>
          Half its {kind} bookings are usually made by {day(hint.date, today)}, so many are in
          already: book soon if there's room.
        </p>
      )}
      <p className="muted">Estimated from past bookings.</p>
    </div>
  )
}
