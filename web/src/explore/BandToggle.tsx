import type { KeyboardEvent } from 'react'
import { BAND_NAMES } from './bands'
import type { Band } from './filters'

const BANDS: Band[] = ['quiet', 'ok', 'busy']

type Props = {
  band: Band
  counts: Record<Band, number>
  onChange: (band: Band) => void
}

// Quiet / Not too busy / Busy, with how many of each: a radio group, so arrow keys move along
// it. The pill slides to the band picked.
export function BandToggle({ band, counts, onChange }: Props) {
  const at = BANDS.indexOf(band)

  function move(e: KeyboardEvent) {
    const step = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key]
    if (step === undefined) return
    e.preventDefault()
    const next = BANDS[(at + step + BANDS.length) % BANDS.length]
    onChange(next)
    e.currentTarget.querySelector<HTMLElement>(`[data-band="${next}"]`)?.focus()
  }

  return (
    <div
      className={`band-toggle band-${band}`}
      role="radiogroup"
      aria-label="How busy"
      onKeyDown={move}
      style={{ '--at': at } as React.CSSProperties}
    >
      <span className="band-pill" aria-hidden="true" />
      {BANDS.map((b) => (
        <button
          key={b}
          type="button"
          role="radio"
          data-band={b}
          aria-checked={b === band}
          tabIndex={b === band ? 0 : -1}
          onClick={() => onChange(b)}
        >
          <span>{BAND_NAMES[b]}</span>
          <span className="band-count">{counts[b].toLocaleString()}</span>
        </button>
      ))}
    </div>
  )
}
