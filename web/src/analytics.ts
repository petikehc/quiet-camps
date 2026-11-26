import type { AnyRouter } from '@tanstack/react-router'

// Page views, counted by GoatCounter (quietcamps.goatcounter.com): no cookies, no personal data.
// Only the path is sent, never the search, which holds the dates and the place someone looked
// for. The script is loaded with no_onload (index.html), so this counts every page the app
// moves to, not just the first; GoatCounter itself skips localhost and bots.

export type GoatCounter = { count: (vars: { path: string }) => void }

declare global {
  interface Window {
    // Settings can be put here before the script loads, so it may exist without count yet.
    goatcounter?: Partial<GoatCounter>
  }
}

// Counts a path, or keeps it until the script has loaded: it's async, and the first page can
// resolve before it arrives.
export function pageCounter(counter: () => Partial<GoatCounter> | undefined) {
  const waiting: string[] = []
  return {
    count(path: string) {
      const count = counter()?.count
      if (count) count({ path })
      else waiting.push(path)
    },
    loaded() {
      const count = counter()?.count
      if (count) for (const path of waiting.splice(0)) count({ path })
    },
  }
}

export function countPages(router: AnyRouter) {
  const pages = pageCounter(() => window.goatcounter)
  document.querySelector('script[data-goatcounter]')?.addEventListener('load', pages.loaded)
  // A new page, not a new search: the explorer's filters live in the URL, and each change
  // resolves the route again.
  router.subscribe('onResolved', (event) => {
    if (event.pathChanged) pages.count(event.toLocation.pathname)
  })
}
