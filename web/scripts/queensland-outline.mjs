// Writes src/timelapse/queensland.json: Queensland's outline for the time-lapse's ground.
// Source: ABS ASGS 2021 State and Territory boundaries, © Commonwealth of Australia (ABS),
// CC BY 4.0. Run it again only if the boundary or the simplification changes:
//   node scripts/queensland-outline.mjs
import { writeFile } from 'node:fs/promises'

const QUERY = new URL('https://geo.abs.gov.au/arcgis/rest/services/ASGS2021/STE/MapServer/0/query')
QUERY.search = new URLSearchParams({
  where: "state_code_2021='3'",
  outFields: 'state_name_2021',
  returnGeometry: 'true',
  maxAllowableOffset: '0.02', // the server drops points closer than ~2 km to the line
  outSR: '4326',
  f: 'geojson',
}).toString()

// About 100 km² at Queensland's latitudes: keeps K'gari, Moreton, the Stradbroke islands,
// Hinchinbrook and the Gulf islands, drops reefs and rocks a column could never sit on.
const MIN_AREA = 0.01 // square degrees

// Shoelace formula, in square degrees: enough to rank polygons by size.
function area(ring) {
  let sum = 0
  for (let i = 0; i < ring.length - 1; i++) {
    sum += ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1]
  }
  return Math.abs(sum) / 2
}

const round = ([lon, lat]) => [Math.round(lon * 1000) / 1000, Math.round(lat * 1000) / 1000]

const response = await fetch(QUERY)
if (!response.ok) throw new Error(`ABS boundary: HTTP ${response.status}`)
const [state] = (await response.json()).features
if (state?.geometry.type !== 'MultiPolygon') throw new Error('Expected one MultiPolygon')

// Outer rings only: the time-lapse draws land, and Queensland's holes are lakes and bays.
const kept = state.geometry.coordinates
  .map((polygon) => polygon[0])
  .filter((ring) => area(ring) >= MIN_AREA)
  .sort((a, b) => area(b) - area(a))
  .map((ring) => [ring.map(round)])

const outline = {
  type: 'Feature',
  properties: {
    name: 'Queensland',
    source:
      'Australian Statistical Geography Standard (ASGS) Edition 3, State and Territory boundaries, ' +
      '© Commonwealth of Australia (Australian Bureau of Statistics), CC BY 4.0. Simplified.',
  },
  geometry: { type: 'MultiPolygon', coordinates: kept },
}
await writeFile(new URL('../src/timelapse/queensland.json', import.meta.url), JSON.stringify(outline))
const points = kept.reduce((n, [ring]) => n + ring.length, 0)
console.log(`${kept.length} of ${state.geometry.coordinates.length} polygons, ${points} points`)
