import {
  createRootRoute,
  createRoute,
  createRouter,
  redirect,
  type SearchSchemaInput,
} from '@tanstack/react-router'
import { CampgroundPage } from './campground/CampgroundPage'
import { parseYear } from './campground/year'
import { ExplorePage } from './explore/ExplorePage'
import {
  isOldSearchLink,
  parseFilters,
  parseView,
  type Filters,
  type View,
} from './explore/filters'
import { HomePage } from './home/HomePage'
import { Layout } from './Layout'

// Code-based routes: with a page or two, one file reads more easily than generated file routes.
const rootRoute = createRootRoute({ component: Layout })

// What /explore keeps in the URL, from whatever a link gave it.
const exploreSearch = (search: Record<string, unknown>) => ({
  ...parseFilters(search),
  ...parseView(search),
})

const homeRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  // Links from when the search was the homepage go on to the explorer, filters and all.
  beforeLoad: ({ search }) => {
    if (isOldSearchLink(search)) {
      throw redirect({ to: '/explore', search: exploreSearch(search), replace: true })
    }
  },
  component: HomePage,
})

const exploreRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/explore',
  // SearchSchemaInput: a link may leave filters out (parseFilters fills in the coming weekend),
  // but the page always gets them all.
  validateSearch: (search: Partial<Filters & View> & SearchSchemaInput) => exploreSearch(search),
  component: ExplorePage,
})

// The search and the 3D time-lapse were folded into the explorer: their links still work.
const searchRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/search',
  validateSearch: (search: Record<string, unknown>) => search,
  beforeLoad: ({ search }) => {
    throw redirect({ to: '/explore', search: exploreSearch(search), replace: true })
  },
})

const timelapseRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/timelapse',
  beforeLoad: () => {
    throw redirect({ to: '/explore', search: exploreSearch({}), replace: true })
  },
})

const campgroundRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/campgrounds/$campgroundId',
  validateSearch: (search: { year?: number } & SearchSchemaInput) => parseYear(search),
  component: CampgroundPage,
})

export const router = createRouter({
  routeTree: rootRoute.addChildren([
    homeRoute,
    exploreRoute,
    searchRoute,
    timelapseRoute,
    campgroundRoute,
  ]),
  scrollRestoration: true, // back to the explorer puts you where you were in the list
})

// Tells useSearch, Link and navigate about these routes, so search params and paths are typed.
declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}
