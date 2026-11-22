import {
  createRootRoute,
  createRoute,
  createRouter,
  redirect,
  type SearchSchemaInput,
} from '@tanstack/react-router'
import { CampgroundPage } from './campground/CampgroundPage'
import { parseYear } from './campground/year'
import { HomePage } from './home/HomePage'
import { Layout } from './Layout'
import {
  isOldSearchLink,
  parseFilters,
  parseView,
  type Filters,
  type View,
} from './search/filters'
import { SearchPage } from './search/SearchPage'
import { parseTimelapseYear } from './timelapse/timelapse'
import { TimelapsePage } from './timelapse/TimelapsePage'

// Code-based routes: with a page or two, one file reads more easily than generated file routes.
const rootRoute = createRootRoute({ component: Layout })

const homeRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  // Links from when the search was the homepage go on to it, filters and all.
  beforeLoad: ({ search }) => {
    if (isOldSearchLink(search)) throw redirect({ to: '/search', search, replace: true })
  },
  component: HomePage,
})

const searchRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/search',
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

const timelapseRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/timelapse',
  validateSearch: (search: { year?: number } & SearchSchemaInput) => parseTimelapseYear(search),
  component: TimelapsePage,
})

export const router = createRouter({
  routeTree: rootRoute.addChildren([homeRoute, searchRoute, campgroundRoute, timelapseRoute]),
  scrollRestoration: true, // back to the results puts you where you were in the list
})

// Tells useSearch, Link and navigate about these routes, so search params and paths are typed.
declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}
