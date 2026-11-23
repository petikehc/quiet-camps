import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { useEffect, useMemo, useRef } from 'react'
import * as THREE from 'three'
import australia from './australia.json'
import {
  DAY,
  flightSeconds,
  inFlight,
  jitter,
  mostInFlight,
  nightOffsets,
  project,
  TRAIL,
  type Trips,
} from './trips'

const SEGMENTS = 24 // straight pieces per trail
const FOV = 32
const TILT = (52 * Math.PI) / 180 // the camera's height above the horizon
// The camera drifts while it plays: a few degrees either way and a little closer and back.
const DRIFT = { turn: (6 * Math.PI) / 180, turnPeriod: 40, zoom: 0.04, zoomPeriod: 53 }

type Props = {
  trips: Trips
  startNight: number
  playing: boolean
  drift: boolean // false when motion is reduced
  quiet: Float32Array // 1 for each campground quiet this week, by index into trips.campgrounds
  onNight: (night: number) => void // when the whole night changes
}

// The homepage's map: every trip as a line from home to campground. WebGL draws it; the page
// puts the words on top in HTML.
export default function TripsScene(props: Props) {
  return (
    <Canvas
      dpr={[1, 2]}
      flat // no tone mapping: the tokens render as the colours they were validated as
      camera={{ fov: FOV, near: 0.5, far: 400 }}
      aria-label="A map of Australia with a line for each camping trip, from home to campground."
    >
      <Land />
      <Flights {...props} />
    </Canvas>
  )
}

// The night palette is the same in light and dark mode, so it's read once.
function useTokens() {
  return useMemo(() => {
    const css = getComputedStyle(document.documentElement)
    const token = (name: string) => new THREE.Color(css.getPropertyValue(name).trim())
    return {
      night: token('--night'),
      land: token('--night-land'),
      line: token('--night-line'),
      tail: token('--trail-tail'),
      trail: token('--trail'),
      head: token('--trail-head'),
      quiet: token('--quiet'),
    }
  }, [])
}

const states = australia.features.map((state) =>
  state.geometry.coordinates.map(([ring]) => ring.map(([lon, lat]) => project(lon, lat))),
)
const rings = states.flat()
const xs = rings.flat().map(([x]) => x)
const zs = rings.flat().map(([, z]) => z)
const BOUNDS = { minX: Math.min(...xs), maxX: Math.max(...xs), minZ: Math.min(...zs), maxZ: Math.max(...zs) }
const CENTRE = new THREE.Vector3((BOUNDS.minX + BOUNDS.maxX) / 2, 0, (BOUNDS.minZ + BOUNDS.maxZ) / 2)

// Land in one flat colour, each state's outline as a line: a quiet stage for the trails.
function Land() {
  const tokens = useTokens()
  const land = useMemo(
    // A shape is drawn in x and y; rotated flat below, its y becomes -z (north).
    () => new THREE.ShapeGeometry(rings.map((r) => new THREE.Shape(r.map(([x, z]) => new THREE.Vector2(x, -z))))),
    [],
  )
  const outlines = useMemo(
    () => rings.map((r) => new THREE.BufferGeometry().setFromPoints(r.map(([x, z]) => new THREE.Vector3(x, 0.01, z)))),
    [],
  )
  useEffect(
    () => () => {
      land.dispose()
      outlines.forEach((o) => o.dispose())
    },
    [land, outlines],
  )

  return (
    <>
      <color attach="background" args={[tokens.night]} />
      <mesh geometry={land} rotation-x={-Math.PI / 2}>
        <meshBasicMaterial color={tokens.land} />
      </mesh>
      {outlines.map((geometry, i) => (
        <lineLoop key={i} geometry={geometry}>
          <lineBasicMaterial color={tokens.line} />
        </lineLoop>
      ))}
    </>
  )
}

// Each trail is the same strip of SEGMENTS lines from t = 0 (home) to 1 (the campground),
// repeated per trip by instancing; the vertex shader bends it into that trip's arc and
// works out how bright each point is from one number, the time. trailAlpha in trips.ts is
// the same sum, with tests.
const TRAIL_VERTEX = /* glsl */ `
  attribute vec4 aEnds;  // home x, z; campground x, z
  attribute vec3 aFlight; // leaves at (seconds into the loop), flight time, sites
  uniform float uTime;
  uniform float uTrail;
  varying float vAlpha;
  varying float vHead;

  void main() {
    float t = position.x;
    float behind = (uTime - aFlight.x) / aFlight.y - t;
    vAlpha = (behind < 0.0 || behind > uTrail) ? 0.0 : 1.0 - behind / uTrail;
    vHead = vAlpha;
    // More sites, a brighter line; overlapping lines add up where many people go.
    vAlpha *= min(1.0, 0.45 + 0.15 * aFlight.z);
    float lift = 4.0 * t * (1.0 - t) * (0.1 + 0.2 * distance(aEnds.xy, aEnds.zw));
    vec2 ground = mix(aEnds.xy, aEnds.zw, t);
    gl_Position = projectionMatrix * modelViewMatrix * vec4(ground.x, lift, ground.y, 1.0);
  }
`
const TRAIL_FRAGMENT = /* glsl */ `
  uniform vec3 uTail;
  uniform vec3 uBody;
  uniform vec3 uHead;
  varying float vAlpha;
  varying float vHead;

  void main() {
    if (vAlpha <= 0.0) discard;
    vec3 colour = vHead < 0.85 ? mix(uTail, uBody, vHead / 0.85) : mix(uBody, uHead, (vHead - 0.85) / 0.15);
    gl_FragColor = vec4(colour, vAlpha);
    #include <colorspace_fragment>
  }
`

// A soft round dot: a campground, brighter and bigger as trips arrive. A quiet one turns
// reef teal and stays lit, so it shows even with hardly anyone arriving.
const CAMP_VERTEX = /* glsl */ `
  attribute float aGlow;
  attribute float aQuiet; // 0 to 1, eased toward this week's quiet
  uniform float uPixelRatio;
  varying float vGlow;
  varying float vQuiet;

  void main() {
    vGlow = aGlow;
    vQuiet = aQuiet;
    gl_PointSize = (2.0 + 7.0 * sqrt(aGlow) + 12.0 * aQuiet) * uPixelRatio;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`
const CAMP_FRAGMENT = /* glsl */ `
  uniform vec3 uColour;
  uniform vec3 uQuiet;
  varying float vGlow;
  varying float vQuiet;

  void main() {
    float d = distance(gl_PointCoord, vec2(0.5));
    float dot = (1.0 - smoothstep(0.2, 0.5, d)) * min(1.0, 0.25 + vGlow);
    // Quiet: a ring with a small core, so it reads as a different kind of place, not a
    // dimmer busy one.
    float ring = smoothstep(0.3, 0.36, d) * (1.0 - smoothstep(0.44, 0.5, d)) + (1.0 - smoothstep(0.1, 0.16, d));
    gl_FragColor = vec4(mix(uColour, uQuiet, vQuiet), mix(dot, ring, vQuiet));
    #include <colorspace_fragment>
  }
`

function Flights({ trips, startNight, playing, drift, quiet, onNight }: Props) {
  const tokens = useTokens()
  const loop = trips.nights * DAY

  // Everything per entry that never changes, worked out once a year: where it flies from
  // and to, when it leaves and how long it flies.
  const plan = useMemo(() => {
    const offsets = nightOffsets(trips.per_night)
    const homes = trips.origins.map((o) => project(o.lon, o.lat))
    const camps = trips.campgrounds.map((c) => project(c.lon, c.lat))
    const count = trips.sites.length
    const ends = new Float32Array(count * 4)
    const flights = new Float32Array(count * 3)
    for (let night = 0; night < trips.nights; night++) {
      for (let e = offsets[night]; e < offsets[night + 1]; e++) {
        const [hx, hz] = homes[trips.origin[e]]
        const [cx, cz] = camps[trips.campground[e]]
        const seconds = flightSeconds(Math.hypot(cx - hx, cz - hz))
        ends.set([hx, hz, cx, cz], e * 4)
        // Lands somewhere in its night, so it leaves a flight earlier.
        flights.set([(night + jitter(e)) * DAY - seconds, seconds, trips.sites[e]], e * 3)
      }
    }
    return { offsets, camps, ends, flights, capacity: mostInFlight(offsets) }
  }, [trips])

  // The GPU holds only the trips that can be in the air tonight; they're copied in when the
  // night changes, a few times a second. Between copies only uTime changes.
  const trails = useMemo(() => {
    const strip = new Float32Array((SEGMENTS * 2) * 3)
    for (let s = 0; s < SEGMENTS; s++) {
      strip[s * 6] = s / SEGMENTS
      strip[s * 6 + 3] = (s + 1) / SEGMENTS
    }
    const geometry = new THREE.InstancedBufferGeometry()
    geometry.setAttribute('position', new THREE.BufferAttribute(strip, 3))
    const ends = new THREE.InstancedBufferAttribute(new Float32Array(plan.capacity * 4), 4)
    const flights = new THREE.InstancedBufferAttribute(new Float32Array(plan.capacity * 3), 3)
    ends.setUsage(THREE.DynamicDrawUsage)
    flights.setUsage(THREE.DynamicDrawUsage)
    geometry.setAttribute('aEnds', ends)
    geometry.setAttribute('aFlight', flights)
    geometry.instanceCount = 0
    const material = new THREE.ShaderMaterial({
      vertexShader: TRAIL_VERTEX,
      fragmentShader: TRAIL_FRAGMENT,
      uniforms: {
        uTime: { value: 0 },
        uTrail: { value: TRAIL },
        uTail: { value: tokens.tail },
        uBody: { value: tokens.trail },
        uHead: { value: tokens.head },
      },
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    })
    return { geometry, material }
  }, [plan, tokens])

  const camps = useMemo(() => {
    const geometry = new THREE.BufferGeometry()
    geometry.setAttribute(
      'position',
      new THREE.BufferAttribute(new Float32Array(plan.camps.flatMap(([x, z]) => [x, 0.02, z])), 3),
    )
    const glow = new THREE.BufferAttribute(new Float32Array(plan.camps.length), 1)
    glow.setUsage(THREE.DynamicDrawUsage)
    geometry.setAttribute('aGlow', glow)
    const calm = new THREE.BufferAttribute(new Float32Array(plan.camps.length), 1)
    calm.setUsage(THREE.DynamicDrawUsage)
    geometry.setAttribute('aQuiet', calm)
    const material = new THREE.ShaderMaterial({
      vertexShader: CAMP_VERTEX,
      fragmentShader: CAMP_FRAGMENT,
      uniforms: { uColour: { value: tokens.head }, uQuiet: { value: tokens.quiet }, uPixelRatio: { value: 1 } },
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    })
    return { geometry, material }
  }, [plan, tokens])

  useEffect(
    () => () => {
      trails.geometry.dispose()
      trails.material.dispose()
      camps.geometry.dispose()
      camps.material.dispose()
    },
    [trails, camps],
  )

  // Changed every frame through refs to what's drawn, as three.js objects are meant to be.
  const lines = useRef<THREE.LineSegments<THREE.InstancedBufferGeometry, THREE.ShaderMaterial>>(null)
  const dots = useRef<THREE.Points<THREE.BufferGeometry, THREE.ShaderMaterial>>(null)
  const time = useRef(startNight * DAY) // seconds into the loop
  const shown = useRef(-1) // the night the buffers were filled for
  const drifted = useRef(0) // seconds of drift, which only moves while playing
  const calmTarget = useRef(quiet) // what aQuiet eases toward, night by night
  useEffect(() => {
    calmTarget.current = quiet
  }, [quiet])
  useEffect(() => {
    time.current = startNight * DAY
    shown.current = -1
  }, [startNight, plan])

  const camera = useThree((state) => state.camera as THREE.PerspectiveCamera)
  const aspect = useThree((state) => state.size.width / state.size.height)
  const dpr = useThree((state) => state.viewport.dpr)
  const view = useMemo(() => frame(aspect), [aspect])

  useFrame((_, delta) => {
    if (!lines.current || !dots.current) return
    if (playing) {
      time.current = (time.current + delta) % loop
      if (drift) drifted.current += delta
    }
    const night = Math.min(trips.nights - 1, Math.floor(time.current / DAY))
    if (night !== shown.current) {
      shown.current = night
      fill(night, lines.current, dots.current)
      onNight(night)
    }
    lines.current.material.uniforms.uTime.value = time.current
    dots.current.material.uniforms.uPixelRatio.value = dpr

    const turn = DRIFT.turn * Math.sin((2 * Math.PI * drifted.current) / DRIFT.turnPeriod)
    const away = view.distance * (1 + DRIFT.zoom * Math.sin((2 * Math.PI * drifted.current) / DRIFT.zoomPeriod))
    camera.position.set(
      view.target.x + away * Math.cos(TILT) * Math.sin(turn),
      away * Math.sin(TILT),
      view.target.z + away * Math.cos(TILT) * Math.cos(turn),
    )
    camera.lookAt(view.target)
  })

  // Copy tonight's window into the buffers, and set each campground's glow from the trips
  // landing on it: tonight's, plus what's left of the last few nights'.
  function fill(night: number, line: NonNullable<typeof lines.current>, dot: NonNullable<typeof dots.current>) {
    const ends = line.geometry.getAttribute('aEnds') as THREE.InstancedBufferAttribute
    const flights = line.geometry.getAttribute('aFlight') as THREE.InstancedBufferAttribute
    let slot = 0
    for (const { from, to, shift } of inFlight(plan.offsets, night)) {
      ends.array.set(plan.ends.subarray(from * 4, to * 4), slot * 4)
      flights.array.set(plan.flights.subarray(from * 3, to * 3), slot * 3)
      for (let i = 0; i < to - from; i++) flights.array[(slot + i) * 3] += shift
      slot += to - from
    }
    line.geometry.instanceCount = slot
    for (const attribute of [ends, flights]) {
      attribute.clearUpdateRanges()
      attribute.addUpdateRange(0, slot * attribute.itemSize)
      attribute.needsUpdate = true
    }

    const glow = dot.geometry.getAttribute('aGlow') as THREE.BufferAttribute
    for (let c = 0; c < glow.count; c++) glow.array[c] *= 0.7
    for (let e = plan.offsets[night]; e < plan.offsets[night + 1]; e++) {
      glow.array[trips.campground[e]] += trips.sites[e] / 20
    }
    glow.needsUpdate = true

    // Quiet fades in and out over a few nights rather than switching with the week.
    const calm = dot.geometry.getAttribute('aQuiet') as THREE.BufferAttribute
    for (let c = 0; c < calm.count; c++) calm.array[c] += (calmTarget.current[c] - calm.array[c]) * 0.4
    calm.needsUpdate = true
  }

  return (
    <>
      <lineSegments ref={lines} geometry={trails.geometry} material={trails.material} frustumCulled={false} />
      <points ref={dots} geometry={camps.geometry} material={camps.material} frustumCulled={false} />
    </>
  )
}

// Where the camera looks and how far back it stands so the whole continent fits, whatever
// the canvas's shape. Tilted, the near (southern) edge looks bigger than the far one, so
// rather than a formula: project the corners through a test camera, step back until they
// fit, and slide the target until they're centred.
const FILL = 0.86 // of the canvas, leaving room for the drift

function frame(aspect: number): { distance: number; target: THREE.Vector3 } {
  const camera = new THREE.PerspectiveCamera(FOV, aspect, 0.5, 400)
  const corners = [BOUNDS.minX, BOUNDS.maxX].flatMap((x) =>
    [BOUNDS.minZ, BOUNDS.maxZ].map((z) => new THREE.Vector3(x, 0, z)),
  )
  const target = CENTRE.clone()
  let distance = 10
  // The camera at `distance` looking at `target`: the corners' extent on screen, -1 to 1.
  const extent = () => {
    camera.position.set(target.x, distance * Math.sin(TILT), target.z + distance * Math.cos(TILT))
    camera.lookAt(target)
    camera.updateMatrixWorld()
    const seen = corners.map((c) => c.clone().project(camera))
    const ys = seen.map((v) => v.y)
    return { x: Math.max(...seen.map((v) => Math.abs(v.x))), top: Math.max(...ys), bottom: Math.min(...ys) }
  }
  for (let i = 0; i < 4; i++) {
    for (let e = extent(); Math.max(e.x, e.top, -e.bottom) > FILL; e = extent()) distance *= 1.02
    for (let e = extent(); Math.max(e.x, e.top, -e.bottom) < FILL * 0.98; e = extent()) distance /= 1.02
    const { top, bottom } = extent()
    target.z -= ((top + bottom) / 2) * (BOUNDS.maxZ - BOUNDS.minZ) * 0.5 // nudge toward centre
  }
  // Wide canvases have the leaderboard over the Tasman Sea: the map moves a little west.
  if (aspect > 1.3) target.x += (BOUNDS.maxX - BOUNDS.minX) * 0.06
  return { distance, target }
}
