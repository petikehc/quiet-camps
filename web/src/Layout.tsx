import { Link, Outlet, useMatchRoute } from '@tanstack/react-router'
import { NightSoundsProvider, SoundSwitch } from './sound/NightSoundsProvider'

export function Layout() {
  // The homepage runs its night map edge to edge, with the header floating over it; the
  // explorer fills the screen under the header, with the data credits in its sidebar. Every
  // other page has its content in the column.
  const matchRoute = useMatchRoute()
  const home = Boolean(matchRoute({ to: '/' }))
  const explore = Boolean(matchRoute({ to: '/explore' }))

  return (
    <NightSoundsProvider>
      <header className={home ? 'site-header over' : 'site-header'}>
        <div className="wrap">
          <h1>
            <Link to="/">
              <svg width="28" height="24" viewBox="0 0 26 22" aria-hidden="true">
                <path
                  d="M13 2 2 20h22L13 2Z"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinejoin="round"
                />
                <path d="M13 9l-4 11h8l-4-11Z" fill="currentColor" />
              </svg>
              Quiet Camps
            </Link>
          </h1>
          <nav className="site-nav" aria-label="Pages">
            <SoundSwitch />
            {/* On the map already: keep your search, so the link to this page doesn't wipe it. */}
            <Link to="/explore" search={explore ? true : undefined} activeOptions={{ includeSearch: false }}>
              Map
            </Link>
          </nav>
        </div>
      </header>
      <main className={home ? undefined : explore ? 'explore-main' : 'wrap'}>
        <Outlet />
      </main>
      {/* wrap sets the column; the border sits on the inner box, so it's as wide as the text. */}
      {!explore && (
      <footer className="wrap">
        <div className="site-footer">
          <p>
            Camping permits:{' '}
            <a href="https://www.data.qld.gov.au/dataset/camping-and-vehicle-permits">
              Camping and vehicle permits
            </a>
            , © State of Queensland,{' '}
            <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>. Locations: ©{' '}
            <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors.
            Boundaries and postal areas: ABS, © Commonwealth of Australia, CC BY 4.0. Night
            sounds: <a href="/sounds/CREDITS.md">public-domain recordings</a> from Freesound.
          </p>
          <p>
            Past bookings, not live availability. Not affiliated with or endorsed by Queensland
            Parks and Wildlife Service or the Queensland Government.
          </p>
        </div>
      </footer>
      )}
    </NightSoundsProvider>
  )
}
