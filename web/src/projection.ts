// Longitude and latitude to a flat ground plane, in degrees of latitude: an equirectangular
// projection squeezed by cos(latitude) at the map's middle, so shapes there keep their
// proportions. North is -z, away from a camera that starts in the south.
export function projection(middle: { lon: number; lat: number }) {
  const squeeze = Math.cos((middle.lat * Math.PI) / 180)
  return (lon: number, lat: number): [x: number, z: number] => [
    (lon - middle.lon) * squeeze,
    -(lat - middle.lat),
  ]
}
