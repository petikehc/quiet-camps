import type { Feature, Polygon } from 'geojson'

// Queensland's land borders, west to east: from the Gulf of Carpentaria down the Northern
// Territory border, along South Australia's, then New South Wales' to the coast at Point Danger.
// From the ABS state outline the homepage draws (home/australia.json, ASGS 2021, CC BY 4.0).
const LAND_BORDER: [number, number][] = [
  [137.99, -16.54], [138, -26], [141, -26], [141, -29], [148.96, -29], [149.5, -28.57],
  [149.7, -28.63], [150.29, -28.54], [150.44, -28.66], [150.75, -28.63], [151.01, -28.74],
  [151.04, -28.84], [151.27, -28.94], [151.34, -29.18], [151.71, -28.87], [151.78, -28.96],
  [152.01, -28.91], [152.08, -28.71], [151.96, -28.52], [152.39, -28.37], [152.46, -28.26],
  [152.58, -28.34], [152.61, -28.27], [152.75, -28.36], [152.88, -28.31], [153.11, -28.36],
  [153.18, -28.25], [153.55, -28.16],
]

// Back round through open sea, where the mask's edge can't be seen: east of the Gold Coast, north
// up the Coral Sea, south of Papua New Guinea's Louisiade islands and its south-east coast,
// between the Torres Strait islands and its southern coast, and back across the Gulf.
const SEA: [number, number][] = [
  [157, -28.16], [157, -12], [150, -11.3], [147.6, -10.6], [144.4, -9.25], [142.9, -9.22],
  [141, -9.2], [137.99, -12],
]

// Everything but Queensland, as one polygon with Queensland as its hole: the explorer's map
// darkens it to the night sea's colour, so the map is about Queensland, not its neighbours.
export const OUTSIDE_QUEENSLAND: Feature<Polygon> = {
  type: 'Feature',
  properties: {},
  geometry: {
    type: 'Polygon',
    coordinates: [
      [[-180, -85], [180, -85], [180, 85], [-180, 85], [-180, -85]],
      [...LAND_BORDER, ...SEA, LAND_BORDER[0]],
    ],
  },
}
