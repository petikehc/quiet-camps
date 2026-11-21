import { getRouteApi, Link } from '@tanstack/react-router'
import type { FormEvent } from 'react'
import type { Filters } from './filters'

const route = getRouteApi('/')

// Submitting navigates to a new URL; the page reads the filters back from it.
export function SearchForm({ filters }: { filters: Filters }) {
  const navigate = route.useNavigate()

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    void navigate({
      search: {
        arrive: String(form.get('arrive')),
        depart: String(form.get('depart')),
        q: String(form.get('q')).trim() || undefined,
        park: filters.park,
      },
    })
  }

  return (
    // Uncontrolled inputs; the key resets them when the URL changes (back, forward, a park link).
    <form className="search-form" key={JSON.stringify(filters)} onSubmit={onSubmit}>
      <label>
        Arrive
        <input type="date" name="arrive" defaultValue={filters.arrive} required />
      </label>
      <label>
        Leave
        <input type="date" name="depart" defaultValue={filters.depart} required />
      </label>
      <label>
        Name or park
        <input type="search" name="q" defaultValue={filters.q} minLength={2} maxLength={100} />
      </label>
      <button type="submit">Search</button>
      {filters.park && (
        <p className="park-filter">
          In {filters.park}{' '}
          <Link from="/" to="/" search={(prev) => ({ ...prev, park: undefined })}>
            Any park
          </Link>
        </p>
      )}
    </form>
  )
}
