import { Link } from '@tanstack/react-router'

export function HomePage() {
  return (
    <article className="home">
      <h2>Find a campground that's usually quiet on your dates</h2>
      <p>
        <Link to="/search" className="cta">
          Find a quiet campground →
        </Link>
      </p>
    </article>
  )
}
