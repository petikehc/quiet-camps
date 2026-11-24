import type { LayerSpecification, StyleSpecification } from 'maplibre-gl'

// The colours the basemap is drawn in, read from the page's tokens.
export type NightColours = {
  land: string
  park: string // national parks and forest: where the campgrounds are
  built: string // towns
  sea: string
  road: string
  label: string
  halo: string
}

// What a layer of OpenFreeMap's dark style shows, by its id. Unlisted layers keep their own
// colours. Order matters: the first match wins.
const FILLS: [RegExp, keyof NightColours][] = [
  [/water/, 'sea'],
  [/park|wood/, 'park'],
  [/residential|building/, 'built'],
  [/ice|glacier|aeroway|pier/, 'land'],
]
const LINES: [RegExp, keyof NightColours, number][] = [
  [/waterway/, 'sea', 1],
  [/boundary/, 'road', 0.5],
  [/casing/, 'road', 0.2],
  [/motorway/, 'road', 0.55],
  [/highway|railway|aeroway|road/, 'road', 0.35],
]

// OpenFreeMap's dark style, recoloured in the site's night: teal-slate land lighter than a
// night sea (the stock style has them the other way round), national parks tinted eucalypt,
// and roads and names in the night's line and muted colours.
export function nightStyle(style: StyleSpecification, colours: NightColours): StyleSpecification {
  return { ...style, layers: style.layers.map((layer) => recolour(layer, colours)) }
}

function recolour(layer: LayerSpecification, c: NightColours): LayerSpecification {
  switch (layer.type) {
    case 'background':
      return { ...layer, paint: { ...layer.paint, 'background-color': c.land } }
    case 'fill': {
      const role = FILLS.find(([pattern]) => pattern.test(layer.id))?.[1]
      if (!role) return layer
      const { 'fill-outline-color': _, ...paint } = layer.paint ?? {}
      return { ...layer, paint: { ...paint, 'fill-color': c[role] } }
    }
    case 'line': {
      const found = LINES.find(([pattern]) => pattern.test(layer.id))
      if (!found) return layer
      const [, role, opacity] = found
      return { ...layer, paint: { ...layer.paint, 'line-color': c[role], 'line-opacity': opacity } }
    }
    case 'symbol':
      if (!layer.paint?.['text-color'] && !layer.paint?.['text-halo-color']) return layer
      return {
        ...layer,
        paint: { ...layer.paint, 'text-color': c.label, 'text-halo-color': c.halo },
      }
    default:
      return layer
  }
}
