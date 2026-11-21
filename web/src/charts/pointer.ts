import type { PointerEvent } from 'react'

export type TooltipAt = { x: number; y: number } // px, relative to the chart's container

export function pointerIn(event: PointerEvent, container: HTMLElement | null): TooltipAt {
  const box = container?.getBoundingClientRect()
  return { x: event.clientX - (box?.left ?? 0), y: event.clientY - (box?.top ?? 0) }
}
