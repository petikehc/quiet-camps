import { getRouteApi, Link } from '@tanstack/react-router'
import { locationNote, osmLink } from './location'
import type { QuietCampground } from './ResultsTable'

const route = getRouteApi('/')

// The campground picked on the map or in the list. A tooltip vanishes with the pointer, so
// the links (its page, and its OpenStreetMap object to check the location) live here.
export function SelectedCampground({ campground }: { campground: QuietCampground }) {
  const { arrive } = route.useSearch()
  const { reasons } = locationNote(campground)
  const osm = osmLink(campground)

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
      {reasons.map((reason) => (
        <div key={reason} className="muted">
          ⚠ {reason}
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
