import type { FeatureCollection } from 'geojson'
import * as maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import { useEffect, useRef, useState } from 'react'
import type { TooltipAt } from '../charts/pointer'
import { Tooltip } from '../charts/Tooltip'
import { BAND_NAMES, bandOf } from './bands'
import type { Band } from './filters'
import { shownLocation, type Certainty } from './location'
import type { QuietCampground } from './queries'

// MapLibre parses tiles in a web worker it loads from a file beside its own module. Vite moves
// the module (the dev pre-bundle, the build) and not the worker, so the map stayed blank.
// ?worker&url makes Vite build the worker as its own file and give us its URL.
maplibregl.setWorkerUrl(workerUrl)

// OpenFreeMap's dark style (OpenStreetMap, no key): the explorer is night, like the homepage,
// whatever the page theme.
const STYLE = 'https://tiles.openfreemap.org/styles/dark'
const QUEENSLAND: [[number, number], [number, number]] = [
  [137.9, -29.2],
  [153.6, -9.1],
]
const CAMPGROUNDS = 'campgrounds'
const PINS = 'campground-points'
const NEAR = 'near'
const DRAW_ORDER: Record<Certainty, number> = { none: 0, park: 1, check: 2, exact: 3 }
const KM_PER_DEGREE = 111.32

export type Near = { lat: number; lon: number; km: number }

type Props = {
  rows: QuietCampground[]
  band: Band // the band listed: its pins are full size, the others small and faint
  selectedId: number | undefined
  highlightId: number | undefined // hovered in the list: drawn like the picked one, no panning
  onSelect: (id: number) => void
  near: Near | undefined // drawn as a circle, and the map fits it
  fitKey: string // a new key (new filters) fits the map once
  review: boolean // ?review=locations: rings for matches that need a check
  onMap: (map: maplibregl.Map | undefined) => void // for the line from a card to its pin
}

// React owns the <div>; MapLibre owns everything drawn inside it. Effects pass data across.
export function ExploreMap({
  rows,
  band,
  selectedId,
  highlightId,
  onSelect,
  near,
  fitKey,
  review,
  onMap,
}: Props) {
  const container = useRef<HTMLDivElement>(null)
  const map = useRef<maplibregl.Map>(undefined)
  const fitted = useRef<string>(undefined) // the fitKey the map was last fitted to
  const [ready, setReady] = useState(false)
  const [hover, setHover] = useState<{ row: QuietCampground; at: TooltipAt }>()

  // Handlers are registered once, so they read the latest props through refs.
  const latest = useRef({ rows, onSelect, onMap })
  useEffect(() => {
    latest.current = { rows, onSelect, onMap }
  })

  useEffect(() => {
    if (!container.current) return
    const created = new maplibregl.Map({
      container: container.current,
      style: STYLE,
      bounds: QUEENSLAND,
      attributionControl: { compact: true },
    })
    created.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-right')
    created.on('load', () => {
      addLayers(created)
      setReady(true)
      latest.current.onMap(created)
    })
    const find = (e: maplibregl.MapLayerMouseEvent) =>
      latest.current.rows.find((r) => r.id === e.features?.[0]?.properties.id)
    created.on('mousemove', PINS, (e) => {
      const row = find(e)
      created.getCanvas().style.cursor = 'pointer'
      if (row) setHover({ row, at: { x: e.point.x, y: e.point.y } })
    })
    created.on('mouseleave', PINS, () => {
      created.getCanvas().style.cursor = ''
      setHover(undefined)
    })
    created.on('click', PINS, (e) => {
      const row = find(e)
      if (row) latest.current.onSelect(row.id)
    })
    map.current = created
    return () => {
      latest.current.onMap(undefined)
      setReady(false)
      created.remove()
    }
  }, [])

  useEffect(() => {
    if (!ready || !map.current) return
    const lit = highlightId ?? selectedId
    map.current.getSource<maplibregl.GeoJSONSource>(CAMPGROUNDS)?.setData(pins(rows, band, lit, review))
  }, [ready, rows, band, selectedId, highlightId, review])

  useEffect(() => {
    if (!ready || !map.current) return
    map.current.getSource<maplibregl.GeoJSONSource>(NEAR)?.setData(circle(near))
  }, [ready, near])

  // Fit once per search, to the circle or else the results, so panning isn't undone.
  useEffect(() => {
    if (!ready || !map.current || fitted.current === fitKey) return
    const bounds = new maplibregl.LngLatBounds()
    if (near) {
      for (const point of ring(near)) bounds.extend(point)
    } else {
      for (const r of rows) if (r.lat !== null && r.lon !== null) bounds.extend([r.lon, r.lat])
    }
    if (bounds.isEmpty()) return
    fitted.current = fitKey
    map.current.fitBounds(bounds, { padding: 48, maxZoom: 10, duration: 0 })
  }, [ready, rows, near, fitKey])

  // A campground picked in the list comes into view, if it isn't already.
  useEffect(() => {
    const row = rows.find((r) => r.id === selectedId)
    if (!ready || !map.current || !row || row.lat === null || row.lon === null) return
    const at: [number, number] = [row.lon, row.lat]
    if (!map.current.getBounds().contains(at)) map.current.easeTo({ center: at })
  }, [ready, rows, selectedId])

  return (
    <div className="explore-map">
      <div
        ref={container}
        className="explore-canvas"
        aria-label="Map of the campgrounds. The list beside it has the same ones."
      />
      {hover && (
        <Tooltip at={hover.at}>
          <PinDetails row={hover.row} review={review} />
        </Tooltip>
      )}
    </div>
  )
}

function pins(
  rows: QuietCampground[],
  band: Band,
  selectedId: number | undefined,
  review: boolean,
): FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: rows.flatMap((r) => {
      if (r.lat === null || r.lon === null) return []
      const { certainty } = shownLocation(r, review)
      const selected = r.id === selectedId
      const pinBand = bandOf(r.busyness)
      const listed = pinBand === band
      return [
        {
          type: 'Feature',
          geometry: { type: 'Point', coordinates: [r.lon, r.lat] },
          properties: {
            id: r.id,
            band: pinBand,
            listed,
            certainty,
            selected,
            // Higher draws on top: the picked one, then the band listed, surest first.
            order: selected ? 20 : (listed ? 10 : 0) + DRAW_ORDER[certainty],
          },
        },
      ]
    }),
  }
}

// The circle around the place, as a 64-sided polygon: km to degrees, wider in longitude
// the further from the equator.
function ring({ lat, lon, km }: Near): [number, number][] {
  const dLat = km / KM_PER_DEGREE
  const dLon = km / (KM_PER_DEGREE * Math.cos((lat * Math.PI) / 180))
  return Array.from({ length: 65 }, (_, i) => {
    const angle = (i / 64) * 2 * Math.PI
    return [lon + dLon * Math.sin(angle), lat + dLat * Math.cos(angle)]
  })
}

function circle(near: Near | undefined): FeatureCollection {
  if (!near) return { type: 'FeatureCollection', features: [] }
  return {
    type: 'FeatureCollection',
    features: [
      { type: 'Feature', geometry: { type: 'Polygon', coordinates: [ring(near)] }, properties: {} },
    ],
  }
}

// The canvas can't read CSS variables, so the colours are read from the page once.
function addLayers(map: maplibregl.Map) {
  const css = getComputedStyle(document.documentElement)
  const token = (name: string) => css.getPropertyValue(name).trim()
  const bandColour: maplibregl.ExpressionSpecification = [
    'match',
    ['get', 'band'],
    'quiet',
    token('--quiet'),
    'ok',
    token('--band-ok'),
    token('--band-busy'),
  ]
  const is = (certainty: Certainty): maplibregl.ExpressionSpecification => [
    '==',
    ['get', 'certainty'],
    certainty,
  ]

  map.addSource(NEAR, { type: 'geojson', data: circle(undefined) })
  map.addLayer({
    id: 'near-fill',
    type: 'fill',
    source: NEAR,
    paint: { 'fill-color': token('--night-text'), 'fill-opacity': 0.04 },
  })
  map.addLayer({
    id: 'near-line',
    type: 'line',
    source: NEAR,
    paint: { 'line-color': token('--night-muted'), 'line-width': 1.5, 'line-dasharray': [2, 2] },
  })

  map.addSource(CAMPGROUNDS, {
    type: 'geojson',
    data: { type: 'FeatureCollection', features: [] },
  })
  map.addLayer({
    id: PINS,
    type: 'circle',
    source: CAMPGROUNDS,
    layout: { 'circle-sort-key': ['get', 'order'] },
    paint: {
      'circle-radius': ['case', ['get', 'selected'], 9, ['get', 'listed'], 6, 3.5],
      // Needs a check: a hollow ring in the band's colour. Otherwise a filled dot.
      'circle-color': ['case', is('check'), token('--night'), bandColour],
      'circle-stroke-color': [
        'case',
        ['get', 'selected'],
        token('--night-text'),
        is('check'),
        bandColour,
        token('--night'),
      ],
      'circle-stroke-width': ['case', ['get', 'selected'], 2.5, is('check'), 2, 1],
      // The other bands stay on the map for context, faint. Park centre only: a faded fill,
      // because the dot isn't where the campground is.
      'circle-opacity': [
        'case',
        ['!', ['get', 'listed']],
        0.3,
        is('park'),
        0.45,
        1,
      ],
      'circle-stroke-opacity': ['case', ['get', 'listed'], 1, 0.3],
    },
  })
}

function PinDetails({ row, review }: { row: QuietCampground; review: boolean }) {
  const { notes } = shownLocation(row, review)
  return (
    <>
      <strong>{row.name}</strong>
      <div>{row.park_name}</div>
      <div>
        {BAND_NAMES[bandOf(row.busyness)]}: usually {Math.round(row.busyness * 100)}% as busy as its
        busy nights
      </div>
      {notes.map((note) => (
        <div key={note} className="muted">
          {note}
        </div>
      ))}
    </>
  )
}
