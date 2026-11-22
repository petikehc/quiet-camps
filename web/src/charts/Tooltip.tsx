import type { ReactNode } from 'react'
import type { TooltipAt } from './pointer'

// One tooltip per chart, placed above the pointer inside a position: relative container.
// It only repeats values the chart's table view also has: it enhances, never gates.
export function Tooltip({ at, children }: { at: TooltipAt; children: ReactNode }) {
  return (
    <div className="tooltip" style={{ left: at.x, top: at.y }} role="presentation">
      {children}
    </div>
  )
}
