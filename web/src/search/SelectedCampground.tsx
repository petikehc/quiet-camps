import { getRouteApi, Link } from '@tanstack/react-router'
import { osmLink, shownLocation } from './location'
import type { QuietCampground } from './ResultsTable'

const route = getRouteApi('/search')

// The campground picked on the map or in the list. A tooltip vanishes with the pointer, so
// the links (its page, and its OpenStreetMap object) live here.
type Props = {
  campground: QuietCampground
  rank: { place: number; of: number } | undefined // its place among all the search's results
  review: boolean
}

export function SelectedCampground({ campground, rank, review }: Props) {
  const { arrive } = route.useSearch()
  const { notes } = shownLocation(campground, review)
  const osm = osmLink(campground, review)

  return (
    <aside className="selected-campground" aria-label="Selected campground">
      <Link
        to="/campgrounds/$campgroundId"
        params={{ campgroundId: String(campground.id) }}
        search={{ year: Number(arrive.slice(0, 4)) }}
      >
        <strong>{campground.name}</strong>
      </Link>{' '}
      <span className="muted">{campground.park_name}</span>
      {rank && (
        // Picked on the map, it may be further down the list than it has loaded.
        <div>
          Ranked {rank.place} of {rank.of} for these nights, usually{' '}
          {Math.round(campground.busyness * 100)}% busy
        </div>
      )}
      {notes.map((note) => (
        <div key={note} className="muted">
          {review && '⚠ '}
          {note}
        </div>
      ))}
      {osm && (
        <div>
          <a href={osm.href} target="_blank" rel="noreferrer">
            {osm.label}
          </a>
        </div>
      )}
    </aside>
  )
}
