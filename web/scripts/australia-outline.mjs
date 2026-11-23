// Writes src/home/australia.json: every state and territory's outline, for the homepage map.
// Source: ABS ASGS 2021 State and Territory boundaries, © Commonwealth of Australia (ABS),
// CC BY 4.0. Run it again only if the boundaries or the simplification change:
//   node scripts/australia-outline.mjs
import { writeFile } from 'node:fs/promises'

const QUERY = new URL('https://geo.abs.gov.au/arcgis/rest/services/ASGS2021/STE/MapServer/0/query')
QUERY.search = new URLSearchParams({
  // 1–8: the states and territories. 9 is Other Territories (Christmas Island and the like),
  // far off the map; Z codes are "outside Australia" and "no usual address".
  where: "state_code_2021 IN ('1','2','3','4','5','6','7','8')",
  outFields: 'state_name_2021',
  returnGeometry: 'true',
  maxAllowableOffset: '0.05', // about 5 km: drawn a whole continent wide, a pixel is more
  outSR: '4326',
  f: 'geojson',
}).toString()

// About 1,000 km² here: keeps Tasmania, Kangaroo Island, the Tiwi Islands, K'gari and
// Groote Eylandt; drops reefs and rocks too small to see.
const MIN_AREA = 0.1 // square degrees

// Shoelace formula, in square degrees: enough to rank polygons by size.
function area(ring) {
  let sum = 0
  for (let i = 0; i < ring.length - 1; i++) {
    sum += ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1]
  }
  return Math.abs(sum) / 2
}

const round = ([lon, lat]) => [Math.round(lon * 100) / 100, Math.round(lat * 100) / 100]

const response = await fetch(QUERY)
if (!response.ok) throw new Error(`ABS boundaries: HTTP ${response.status}`)
const { features } = await response.json()
if (features.length !== 8) throw new Error(`Expected 8 states and territories, got ${features.length}`)

// Outer rings only: the map draws land, and the holes are lakes and bays.
const states = features.map((state) => {
  const polygons = state.geometry.type === 'Polygon' ? [state.geometry.coordinates] : state.geometry.coordinates
  const kept = polygons
    .map((polygon) => polygon[0])
    .filter((ring) => area(ring) >= MIN_AREA)
    .sort((a, b) => area(b) - area(a))
    .map((ring) => [ring.map(round)])
  return {
    type: 'Feature',
    properties: { name: state.properties.state_name_2021 },
    geometry: { type: 'MultiPolygon', coordinates: kept },
  }
})

const outline = {
  type: 'FeatureCollection',
  source:
    'Australian Statistical Geography Standard (ASGS) Edition 3, State and Territory boundaries, ' +
    '© Commonwealth of Australia (Australian Bureau of Statistics), CC BY 4.0. Simplified.',
  features: states,
}
await writeFile(new URL('../src/home/australia.json', import.meta.url), JSON.stringify(outline))
for (const state of states) {
  const rings = state.geometry.coordinates
  const points = rings.reduce((n, [ring]) => n + ring.length, 0)
  console.log(`${state.properties.name}: ${rings.length} polygons, ${points} points`)
}
