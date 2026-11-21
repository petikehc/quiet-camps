import { Link, Outlet } from '@tanstack/react-router'

export function Layout() {
  return (
    <>
      <header className="site-header">
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
          <p>Queensland campgrounds that are usually quiet on your dates.</p>
          <nav className="site-nav" aria-label="Pages">
            <Link to="/" activeOptions={{ includeSearch: false }}>
              Search
            </Link>
            <Link to="/timelapse">A year in 3D</Link>
          </nav>
        </div>
      </header>
      <main className="wrap">
        <Outlet />
      </main>
      {/* wrap sets the column; the border sits on the inner box, so it's as wide as the text. */}
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
          </p>
          <p>
            Past bookings, not live availability. Not affiliated with or endorsed by Queensland
            Parks and Wildlife Service or the Queensland Government.
          </p>
        </div>
      </footer>
    </>
  )
}
