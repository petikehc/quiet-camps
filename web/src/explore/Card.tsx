import { Link } from '@tanstack/react-router'
import type { Holiday } from '../charts/dates'
import { rankWords, usually } from './bands'
import { BookingHint } from './BookingHint'
import { osmLink, shownLocation } from './location'
import type { QuietCampground } from './queries'

type Props = {
  campground: QuietCampground
  selected: boolean
  rank: number // its place among all the results, quietest first
  of: number
  arrive: string
  holiday: Holiday | undefined // the holiday the arrival falls in, if any
  today: string
  review: boolean
  onSelect: () => void
  onHover: (on: boolean) => void
}

export function Card({
  campground: c,
  selected,
  rank,
  of,
  arrive,
  holiday,
  today,
  review,
  onSelect,
  onHover,
}: Props) {
  const { notes } = shownLocation(c, review)
  const osm = osmLink(c, review)
  return (
    <li className={selected ? 'card selected' : 'card'} data-id={c.id}>
      <button
        type="button"
        className="card-main"
        aria-expanded={selected}
        onClick={onSelect}
        onMouseEnter={() => onHover(true)}
        onMouseLeave={() => onHover(false)}
        onFocus={() => onHover(true)}
        onBlur={() => onHover(false)}
      >
        <span className="card-name">{c.name}</span>
        <span className="card-meta">
          {c.park_name}
          {c.distance_km !== null && ` · ${Math.round(c.distance_km)} km`}
        </span>
        <span className="card-usual">{usually(c)}</span>
      </button>
      {selected && (
        <div className="card-more">
          <BookingHint campgroundId={c.id} arrive={arrive} holiday={holiday} today={today} />
          <p>{rankWords(rank, of)}</p>
          {notes.map((note) => (
            <p key={note} className="muted">
              {note}
            </p>
          ))}
          <p className="card-links">
            <Link
              to="/campgrounds/$campgroundId"
              params={{ campgroundId: String(c.id) }}
              search={{ year: Number(arrive.slice(0, 4)) }}
            >
              Its year, night by night
            </Link>
            {osm && (
              <a href={osm.href} target="_blank" rel="noreferrer">
                {osm.label}
              </a>
            )}
          </p>
        </div>
      )}
    </li>
  )
}
