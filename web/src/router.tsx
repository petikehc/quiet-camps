import {
  createRootRoute,
  createRoute,
  createRouter,
  type SearchSchemaInput,
} from '@tanstack/react-router'
import { CampgroundPage } from './campground/CampgroundPage'
import { parseYear } from './campground/year'
import { Layout } from './Layout'
import { parseFilters, parseView, type Filters, type View } from './search/filters'
import { SearchPage } from './search/SearchPage'

// Code-based routes: with a page or two, one file reads more easily than generated file routes.
const rootRoute = createRootRoute({ component: Layout })

const searchRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  // SearchSchemaInput: a link may leave filters out (parseFilters fills in the coming weekend),
  // but the page always gets them all.
  validateSearch: (search: Partial<Filters & View> & SearchSchemaInput) => ({
    ...parseFilters(search),
    ...parseView(search),
  }),
  component: SearchPage,
})

const campgroundRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/campgrounds/$campgroundId',
  validateSearch: (search: { year?: number } & SearchSchemaInput) => parseYear(search),
  component: CampgroundPage,
})

export const router = createRouter({
  routeTree: rootRoute.addChildren([searchRoute, campgroundRoute]),
  scrollRestoration: true, // back to the results puts you where you were in the list
})

// Tells useSearch, Link and navigate about these routes, so search params and paths are typed.
declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}
