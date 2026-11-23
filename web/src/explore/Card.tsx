import { Link } from '@tanstack/react-router'
import { usually } from './bands'
import { osmLink, shownLocation } from './location'
import type { QuietCampground } from './queries'

type Props = {
  campground: QuietCampground
  selected: boolean
  rank: number // its place among all the results, quietest first
  of: number
  year: number // for the campground page's calendar
  review: boolean
  onSelect: () => void
  onHover: (on: boolean) => void
}

export function Card({ campground: c, selected, rank, of, year, review, onSelect, onHover }: Props) {
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
          <p>
            Number {rank} of {of} for these nights, quietest first.
          </p>
          {notes.map((note) => (
            <p key={note} className="muted">
              {note}
            </p>
          ))}
          <p className="card-links">
            <Link
              to="/campgrounds/$campgroundId"
              params={{ campgroundId: String(c.id) }}
              search={{ year }}
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
