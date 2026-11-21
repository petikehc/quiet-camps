import { HEAT_LABELS } from './scales'

// The five busyness colours, as legend items: the calendar and the map share them.
export function HeatKeys() {
  return HEAT_LABELS.map((label, bin) => (
    <li key={label}>
      <span className="swatch" style={{ background: `var(--heat-${bin})` }} />
      {label}
    </li>
  ))
}
