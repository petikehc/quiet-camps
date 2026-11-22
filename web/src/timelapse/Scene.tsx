import { OrbitControls } from '@react-three/drei'
import { Canvas, useFrame, useThree, type ThreeEvent } from '@react-three/fiber'
import { useEffect, useMemo, useRef } from 'react'
import * as THREE from 'three'
import { heatBin } from '../charts/scales'
import { useDarkMode } from '../useDarkMode'
import queensland from './queensland.json'
import { peaks, project, type Year } from './timelapse'

const COLUMN = 0.14 // a column's width: about 15 km
const TALLEST = 6 // the year's busiest campground-night, in ground units
const EASE = 10 // per second: how fast a column catches up after a jump
// The camera looks at the east coast, where nearly every campground is, not at the middle.
const TARGET: [number, number, number] = [2.5, 0, 2.5]
const CAMERA: [number, number, number] = [-2.5, 10.5, 16]
const WIDE = 1.8 // the canvas shape CAMERA was framed for (width / height)

export type Hover = { row: number; clientX: number; clientY: number }

type Props = {
  year: Year
  seekTo: { night: number } // the page moves the time-lapse by passing a new one
  playing: boolean
  speed: number // nights per second
  onNight: (night: number) => void // when the whole night changes
  onEnd: () => void
  onHover: (hover: Hover | undefined) => void
}

// WebGL draws on a canvas; three.js and react-three-fiber turn this JSX into a scene graph.
export default function Scene(props: Props) {
  return (
    <Canvas
      camera={{ position: CAMERA, fov: 40 }}
      dpr={[1, 2]}
      flat // no tone mapping: the page's tokens render as the colours they were validated as
      aria-label="Queensland in 3D: a column per campground, as tall as its campers that night. The chart below has the statewide numbers."
    >
      <ambientLight intensity={1.6} />
      <directionalLight position={[-6, 12, 8]} intensity={1.4} />
      <FitCamera />
      <Ground />
      <Columns {...props} />
      <OrbitControls
        target={TARGET}
        enablePan={false}
        minDistance={6}
        maxDistance={40}
        maxPolarAngle={Math.PI / 2.2} // never under the ground
      />
    </Canvas>
  )
}

// The field of view is vertical, so a narrow canvas (a phone) crops the sides: step back in
// proportion until the state fits across again.
function FitCamera() {
  const camera = useThree((state) => state.camera)
  const aspect = useThree((state) => state.size.width / state.size.height)
  useEffect(() => {
    const target = new THREE.Vector3(...TARGET)
    const offset = new THREE.Vector3(...CAMERA).sub(target).multiplyScalar(Math.max(1, WIDE / aspect))
    camera.position.copy(target.add(offset))
  }, [camera, aspect])
  return null
}

// The canvas can't read CSS variables: the colours come from the page's tokens, per theme.
function useTokens() {
  const dark = useDarkMode()
  return useMemo(() => {
    const css = getComputedStyle(document.documentElement)
    const token = (name: string) => new THREE.Color(css.getPropertyValue(name).trim())
    return {
      dark, // the theme these were read for: a new theme reads them again
      // The heat ramp's quietest step is validated against --surface (2:1 or more).
      ground: token('--surface'),
      coast: token('--muted'),
      heat: [0, 1, 2, 3, 4].map((bin) => token(`--heat-${bin}`)),
    }
  }, [dark])
}

const rings = queensland.geometry.coordinates.map(([ring]) =>
  ring.map(([lon, lat]) => project(lon, lat)),
)

// Flat land in the chart surface colour, unlit so it stays exactly that colour, with the
// coast drawn as a line: the shape reads without a fill that competes with the columns.
function Ground() {
  const { ground, coast } = useTokens()
  const land = useMemo(
    // A shape is drawn in x and y; rotated flat below, its y becomes -z (north).
    () => new THREE.ShapeGeometry(rings.map((r) => new THREE.Shape(r.map(([x, z]) => new THREE.Vector2(x, -z))))),
    [],
  )
  const coasts = useMemo(
    () => rings.map((r) => new THREE.BufferGeometry().setFromPoints(r.map(([x, z]) => new THREE.Vector3(x, 0.002, z)))),
    [],
  )
  useEffect(
    () => () => {
      land.dispose()
      coasts.forEach((c) => c.dispose())
    },
    [land, coasts],
  )

  return (
    <>
      <mesh geometry={land} rotation-x={-Math.PI / 2}>
        <meshBasicMaterial color={ground} />
      </mesh>
      {coasts.map((geometry, i) => (
        <lineLoop key={i} geometry={geometry}>
          <lineBasicMaterial color={coast} />
        </lineLoop>
      ))}
    </>
  )
}

// One draw call for every campground: an InstancedMesh repeats a box with a matrix (where and
// how tall) and a colour per instance.
function Columns({ year, seekTo, playing, speed, onNight, onEnd, onHover }: Props) {
  const { heat } = useTokens()
  const mesh = useRef<THREE.InstancedMesh>(null)
  const shown = useRef(-1) // the whole night the colours were last set for
  // Where the time-lapse is, in nights from 1 January: fractional while it plays, so the
  // columns move between nights rather than stepping.
  const position = useRef(0)
  useEffect(() => {
    position.current = seekTo.night
  }, [seekTo])

  // Only located campgrounds get a column; `rows` maps an instance to its campground's row.
  const layout = useMemo(() => {
    const rows: number[] = []
    const places: [number, number][] = []
    year.campgrounds.forEach((c, row) => {
      if (c.lat === null || c.lon === null) return
      rows.push(row)
      places.push(project(c.lon, c.lat))
    })
    const peak = peaks(year)
    return { rows, places, peak, unit: TALLEST / Math.max(1, ...peak) }
  }, [year])
  const heights = useRef<Float32Array>(new Float32Array(0)) // what each column shows now

  const box = useMemo(() => new THREE.BoxGeometry(COLUMN, 1, COLUMN).translate(0, 0.5, 0), [])
  useEffect(() => () => box.dispose(), [box])

  // A new year (or theme) starts from flat columns and repaints on the next frame.
  useEffect(() => {
    heights.current = new Float32Array(layout.rows.length)
    shown.current = -1
  }, [layout, heat])

  const matrix = useMemo(() => new THREE.Matrix4(), [])
  const reducedMotion = useMemo(() => matchMedia('(prefers-reduced-motion: reduce)').matches, [])

  useFrame((_, delta) => {
    const instances = mesh.current
    if (!instances || heights.current.length !== layout.rows.length) return
    const last = year.nights - 1
    // Math.min: a shorter year (the one the history ends in) after a longer one.
    position.current = Math.min(last, position.current + (playing ? delta * speed : 0))
    const night = Math.floor(position.current)
    const between = position.current - night // 0 to 1, on the way to the next night
    if (playing && position.current >= last) onEnd()

    const campers = (row: number, n: number) => year.values[row * year.nights + n]
    if (night !== shown.current) {
      shown.current = night
      onNight(night)
      layout.rows.forEach((row, i) => {
        const share = campers(row, night) / (layout.peak[row] || 1)
        instances.setColorAt(i, heat[heatBin(share)])
      })
      if (instances.instanceColor) instances.instanceColor.needsUpdate = true
    }

    // Each column eases toward its height between tonight and tomorrow night: smooth while
    // playing, and a short glide instead of a jump when the scrubber moves.
    const ease = reducedMotion ? 1 : 1 - Math.exp(-delta * EASE)
    const next = Math.min(last, night + 1)
    layout.rows.forEach((row, i) => {
      const target = (campers(row, night) * (1 - between) + campers(row, next) * between) * layout.unit
      const height = heights.current[i] + (target - heights.current[i]) * ease
      heights.current[i] = height
      const [x, z] = layout.places[i]
      matrix.makeScale(1, Math.max(height, 0.0001), 1).setPosition(x, 0, z)
      instances.setMatrixAt(i, matrix)
    })
    instances.instanceMatrix.needsUpdate = true
    instances.computeBoundingSphere() // the pointer's ray tests against it
  })

  function hover(event: ThreeEvent<PointerEvent>) {
    event.stopPropagation() // the nearest column only, not the ones behind it
    if (event.instanceId === undefined) return
    const { clientX, clientY } = event.nativeEvent
    onHover({ row: layout.rows[event.instanceId], clientX, clientY })
  }

  return (
    <instancedMesh
      // A new count needs a new mesh: three.js sizes its buffers once.
      key={layout.rows.length}
      ref={mesh}
      args={[box, undefined, layout.rows.length]}
      onPointerMove={hover}
      onPointerOut={() => onHover(undefined)}
    >
      <meshLambertMaterial />
    </instancedMesh>
  )
}
