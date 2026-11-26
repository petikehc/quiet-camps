import type { AnyRouter } from '@tanstack/react-router'

// Page views and a few events, counted by GoatCounter (quietcamps.goatcounter.com): no cookies,
// no personal data. What happened is counted, never what someone typed or picked: paths without
// their search (it holds the dates and the place), links by where they go, /ask by how it went.
// The script is loaded with no_onload (index.html), so this counts every page the app moves
// to, not just the first; GoatCounter itself skips localhost and bots.

export type Count = { path: string; event?: boolean }
export type GoatCounter = { count: (vars: Count) => void }

declare global {
  interface Window {
    // Settings can be put here before the script loads, so it may exist without count yet.
    goatcounter?: Partial<GoatCounter>
  }
}

// Sends a count, or keeps it until the script has loaded: it's async, and the first page can
// resolve before it arrives.
export function counter(goat: () => Partial<GoatCounter> | undefined) {
  const waiting: Count[] = []
  return {
    count(vars: Count) {
      const count = goat()?.count
      if (count) count(vars)
      else waiting.push(vars)
    },
    loaded() {
      const count = goat()?.count
      if (count) for (const vars of waiting.splice(0)) count(vars)
    },
  }
}

const counts = counter(() => window.goatcounter)

// An event, by name: "sounds: on", "band: busy", "ask: understood".
export function countEvent(name: string) {
  counts.count({ path: name, event: true })
}

const TEXT = 60 // a link's words, at most

// "link: /explore · Or browse the map", "out: parks.qld.gov.au/parks/… · Camping area on QPWS":
// where a link goes, without its search, and what it says. Undefined for a link to nowhere.
export function linkEvent(href: string, text: string, origin: string): string | undefined {
  const url = new URL(href, origin)
  if (!url.protocol.startsWith('http') || url.hash) return undefined
  const words = text.replace(/\s+/g, ' ').trim()
  const said = words.length > TEXT ? `${words.slice(0, TEXT - 1)}…` : words
  const where = url.origin === origin ? `link: ${url.pathname}` : `out: ${url.host}${url.pathname}`
  return said ? `${where} · ${said}` : where
}

// Middle-click opens a link too; a click with a modifier the browser doesn't open it for (Alt
// downloads it) isn't counted.
function countLink(event: MouseEvent) {
  if (event.button > 1 || event.altKey) return
  const link = event.target instanceof Element ? event.target.closest('a[href]') : null
  if (!(link instanceof HTMLAnchorElement)) return
  const name = linkEvent(link.href, link.innerText, location.origin)
  if (name) countEvent(name)
}

export function startCounting(router: AnyRouter) {
  document.querySelector('script[data-goatcounter]')?.addEventListener('load', counts.loaded)
  // A new page, not a new search: the explorer's filters live in the URL, and each change
  // resolves the route again.
  router.subscribe('onResolved', (event) => {
    if (event.pathChanged) counts.count({ path: event.toLocation.pathname })
  })
  // On the document, before anything else: every link, including those React adds later and
  // any whose own handler stops the click there.
  document.addEventListener('click', countLink, { capture: true })
  document.addEventListener('auxclick', countLink, { capture: true })
}
