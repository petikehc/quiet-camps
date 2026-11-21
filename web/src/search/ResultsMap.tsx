import type { FeatureCollection } from 'geojson'
import * as maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import { useEffect, useRef, useState } from 'react'
import { HeatKeys } from '../charts/HeatKeys'
import type { TooltipAt } from '../charts/pointer'
import { heatBin } from '../charts/scales'
import { Tooltip } from '../charts/Tooltip'
import { useDarkMode } from '../useDarkMode'
import { locationNote, type Certainty } from './location'
import type { QuietCampground } from './ResultsTable'

// MapLibre parses tiles in a web worker it loads from a file beside its own module. Vite moves
// the module (the dev pre-bundle, the build) and not the worker, so the map stayed blank.
// ?worker&url makes Vite build the worker as its own file and give us its URL.
maplibregl.setWorkerUrl(workerUrl)

// OpenFreeMap: free vector tiles from OpenStreetMap, no key. Muted styles, so the data stands out.
const STYLE = {
  light: 'https://tiles.openfreemap.org/styles/positron',
  dark: 'https://tiles.openfreemap.org/styles/dark',
}
const QUEENSLAND: [[number, number], [number, number]] = [
  [137.9, -29.2],
  [153.6, -9.1],
]
const SOURCE = 'campgrounds'
const LAYER = 'campground-points'
const DRAW_ORDER: Record<Certainty, number> = { none: 0, park: 1, check: 2, exact: 3 }

type Props = {
  rows: QuietCampground[]
  selectedId: number | undefined
  onSelect: (id: number) => void
  fitKey: string // a new key (new filters) fits the map to the results once
}

// React owns the <div>; MapLibre owns everything drawn inside it. Effects pass data across.
export function ResultsMap({ rows, selectedId, onSelect, fitKey }: Props) {
  const container = useRef<HTMLDivElement>(null)
  const map = useRef<maplibregl.Map>(undefined)
  const fitted = useRef<string>(undefined) // the fitKey the map was last fitted to
  const [ready, setReady] = useState(false)
  const [hover, setHover] = useState<{ row: QuietCampground; at: TooltipAt }>()
  const dark = useDarkMode()

  // Handlers are registered once, so they read the latest props through refs.
  const latest = useRef({ rows, onSelect })
  useEffect(() => {
    latest.current = { rows, onSelect }
  })

  useEffect(() => {
    if (!container.current) return
    const created = new maplibregl.Map({
      container: container.current,
      style: dark ? STYLE.dark : STYLE.light,
      bounds: QUEENSLAND,
      attributionControl: { compact: true },
    })
    created.addControl(new maplibregl.NavigationControl({ showCompass: false }))
    created.on('load', () => {
      addLayers(created)
      setReady(true)
    })
    const find = (e: maplibregl.MapLayerMouseEvent) =>
      latest.current.rows.find((r) => r.id === e.features?.[0]?.properties.id)
    created.on('mousemove', LAYER, (e) => {
      const row = find(e)
      created.getCanvas().style.cursor = 'pointer'
      if (row) setHover({ row, at: { x: e.point.x, y: e.point.y } })
    })
    created.on('mouseleave', LAYER, () => {
      created.getCanvas().style.cursor = ''
      setHover(undefined)
    })
    created.on('click', LAYER, (e) => {
      const row = find(e)
      if (row) latest.current.onSelect(row.id)
    })
    map.current = created
    fitted.current = undefined // a new map (the theme changed) starts unfitted
    return () => {
      setReady(false)
      created.remove()
    }
  }, [dark])

  useEffect(() => {
    if (!ready || !map.current) return
    map.current.getSource<maplibregl.GeoJSONSource>(SOURCE)?.setData(features(rows, selectedId))
  }, [ready, rows, selectedId])

  // Fit to the results once per search, not on every page the infinite scroll adds.
  useEffect(() => {
    if (!ready || !map.current || fitted.current === fitKey) return
    const located = rows.filter((r) => r.lat !== null && r.lon !== null)
    if (located.length === 0) return
    fitted.current = fitKey
    const bounds = new maplibregl.LngLatBounds()
    for (const r of located) bounds.extend([r.lon ?? 0, r.lat ?? 0])
    map.current.fitBounds(bounds, { padding: 40, maxZoom: 10, duration: 0 })
  }, [ready, rows, fitKey])

  // A campground picked in the list comes into view, if it isn't already.
  useEffect(() => {
    const row = rows.find((r) => r.id === selectedId)
    if (!ready || !map.current || !row || row.lat === null || row.lon === null) return
    const at: [number, number] = [row.lon, row.lat]
    if (!map.current.getBounds().contains(at)) map.current.easeTo({ center: at })
  }, [ready, rows, selectedId])

  return (
    <div className="results-map">
      <div
        ref={container}
        className="map-canvas"
        aria-label="Map of the results. The table lists the same campgrounds."
      />
      {hover && (
        <Tooltip at={hover.at}>
          <PinDetails row={hover.row} />
        </Tooltip>
      )}
      <ul className="legend map-legend">
        <HeatKeys />
      </ul>
      <ul className="legend map-legend">
        <li>
          <span className="pin pin-exact" /> Located
        </li>
        <li>
          <span className="pin pin-check" /> Location needs a check
        </li>
        <li>
          <span className="pin pin-park" /> Park centre only
        </li>
      </ul>
    </div>
  )
}

function features(rows: QuietCampground[], selectedId: number | undefined): FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: rows.flatMap((r) => {
      const { certainty } = locationNote(r)
      if (r.lat === null || r.lon === null) return []
      const selected = r.id === selectedId
      return [
        {
          type: 'Feature',
          geometry: { type: 'Point', coordinates: [r.lon, r.lat] },
          properties: {
            id: r.id,
            bin: heatBin(r.busyness),
            certainty,
            selected,
            order: selected ? 10 : DRAW_ORDER[certainty], // higher draws on top
          },
        },
      ]
    }),
  }
}

// The canvas can't read CSS variables, so the chart colours are read from the page once.
function addLayers(map: maplibregl.Map) {
  const css = getComputedStyle(document.documentElement)
  const token = (name: string) => css.getPropertyValue(name).trim()
  const heat = [0, 1, 2, 3, 4].map((bin) => token(`--heat-${bin}`))
  // to-color: an item taken from a list of strings is a string until it's converted.
  const binColour: maplibregl.ExpressionSpecification = [
    'to-color',
    ['at', ['get', 'bin'], ['literal', heat]],
  ]
  const is = (certainty: Certainty): maplibregl.ExpressionSpecification => [
    '==',
    ['get', 'certainty'],
    certainty,
  ]

  map.addSource(SOURCE, { type: 'geojson', data: { type: 'FeatureCollection', features: [] } })
  map.addLayer({
    id: LAYER,
    type: 'circle',
    source: SOURCE,
    layout: { 'circle-sort-key': ['get', 'order'] },
    paint: {
      'circle-radius': ['case', ['get', 'selected'], 9, 6],
      // Needs a check: a hollow ring in the busyness colour. Otherwise a filled dot.
      'circle-color': ['case', is('check'), token('--bg'), binColour],
      'circle-stroke-color': [
        'case',
        ['get', 'selected'],
        token('--text'),
        is('check'),
        binColour,
        token('--pin-ring'), // a halo: quiet pins are the darkest on a dark map, and the point
      ],
      'circle-stroke-width': ['case', ['get', 'selected'], 3, is('check'), 2.5, 1.5],
      // Park centre only: a faded fill, because the dot isn't where the campground is. The
      // ring stays, so the pin is still easy to find.
      'circle-opacity': ['case', is('park'), 0.35, 1],
    },
  })
}

function PinDetails({ row }: { row: QuietCampground }) {
  const { reasons } = locationNote(row)
  return (
    <>
      <strong>{row.name}</strong>
      <div>{row.park_name}</div>
      <div>Usually {Math.round(row.busyness * 100)}% busy</div>
      {reasons.map((reason) => (
        <div key={reason} className="muted">
          ⚠ {reason}
        </div>
      ))}
    </>
  )
}
