import { getRouteApi, Link } from '@tanstack/react-router'
import { osmLink, shownLocation } from './location'
import type { QuietCampground } from './ResultsTable'

const route = getRouteApi('/')

// The campground picked on the map or in the list. A tooltip vanishes with the pointer, so
// the links (its page, and its OpenStreetMap object) live here.
export function SelectedCampground(props: { campground: QuietCampground; review: boolean }) {
  const { campground, review } = props
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
