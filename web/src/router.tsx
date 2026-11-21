import { createRootRoute, createRoute, createRouter } from '@tanstack/react-router'
import { Layout } from './Layout'
import { parseFilters } from './search/filters'
import { SearchPage } from './search/SearchPage'

// Code-based routes: with a page or two, one file reads more easily than generated file routes.
const rootRoute = createRootRoute({ component: Layout })

const searchRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  validateSearch: (search) => parseFilters(search),
  component: SearchPage,
})

export const router = createRouter({ routeTree: rootRoute.addChildren([searchRoute]) })

// Tells useSearch, Link and navigate about these routes, so search params and paths are typed.
declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}
