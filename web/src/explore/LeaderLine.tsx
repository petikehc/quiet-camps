import type * as maplibregl from 'maplibre-gl'
import { useEffect, useState, type RefObject } from 'react'

type Props = {
  map: maplibregl.Map | undefined
  root: RefObject<HTMLElement | null> // the explorer: the line is drawn in its coordinates
  list: RefObject<HTMLElement | null> // the scrolling list of cards
  id: number | undefined // the card hovered or picked
  lat: number | null | undefined
  lon: number | null | undefined
}

// One line from the hovered or picked card to its pin, redrawn as the map moves or the list
// scrolls. Only when both ends are on screen; phones don't show it (CSS).
export function LeaderLine({ map, root, list, id, lat, lon }: Props) {
  const [path, setPath] = useState<string>()

  useEffect(() => {
    let frame = 0
    const draw = () => {
      cancelAnimationFrame(frame)
      frame = requestAnimationFrame(() => setPath(measure()))
    }
    const measure = (): string | undefined => {
      if (!map || id === undefined || lat == null || lon == null || !root.current) return
      const card = root.current.querySelector<HTMLElement>(`[data-id="${id}"]`)
      const listBox = list.current?.getBoundingClientRect()
      if (!card || !listBox) return
      const base = root.current.getBoundingClientRect()
      const box = card.getBoundingClientRect()
      const canvas = map.getContainer().getBoundingClientRect()
      const at = map.project([lon, lat])
      const cardShown = box.bottom > listBox.top + 8 && box.top < listBox.bottom - 8
      const pinShown = at.x >= 0 && at.y >= 0 && at.x <= canvas.width && at.y <= canvas.height
      if (!cardShown || !pinShown) return
      const from = {
        x: box.right - base.left,
        y: Math.min(Math.max(box.top + box.height / 2, listBox.top), listBox.bottom) - base.top,
      }
      const to = { x: canvas.left - base.left + at.x, y: canvas.top - base.top + at.y }
      const bend = (from.x + to.x) / 2
      return `M${from.x},${from.y} C${bend},${from.y} ${bend},${to.y} ${to.x},${to.y}`
    }

    draw()
    const scroller = list.current
    map?.on('move', draw)
    scroller?.addEventListener('scroll', draw, { passive: true })
    window.addEventListener('resize', draw)
    return () => {
      cancelAnimationFrame(frame)
      map?.off('move', draw)
      scroller?.removeEventListener('scroll', draw)
      window.removeEventListener('resize', draw)
    }
  }, [map, root, list, id, lat, lon])

  if (!path) return null
  return (
    <svg className="leader-line" aria-hidden="true">
      <path d={path} />
    </svg>
  )
}
