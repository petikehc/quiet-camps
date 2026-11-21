import { Outlet } from '@tanstack/react-router'

export function Layout() {
  return (
    <>
      <header className="site-header">
        <h1>Quiet Camps</h1>
        <p>Queensland campgrounds that are usually quiet on your dates.</p>
      </header>
      <main>
        <Outlet />
      </main>
      <footer className="site-footer">
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
      </footer>
    </>
  )
}
