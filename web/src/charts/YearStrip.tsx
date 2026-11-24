import { useEffect, useMemo, useRef, useState } from 'react'
import type { Holiday } from './dates'
import { monthStarts, placeLabels, type Label } from './strip'

const W = 1000 // the strip's drawing units; it stretches to its box
const H = 100
const NO_LABELS: Label[] = []
const LABEL_CHAR_PX = 7 // about the width of a character of a peak's label (0.75rem, semibold)

type Props = {
  firstNight: string // YYYY-MM-DD of night 0
  values: (number | null)[] // one per night; null: nothing to show (all closed)
  holidays: Holiday[] // nights counted from firstNight
  schoolHolidays?: Holiday[] // a broader shade, behind the public holidays
  night: number // where the playhead is
  onSeek: (night: number) => void
  labels?: Label[] // named moments above the strip, the most important first
  stay?: { from: number; to: number } // nights to mark: [from, to)
  ariaLabel: string
  valueText: (night: number) => string // what the slider says at a night
}

// A year of nights as one shape, holidays shaded, moments named. The slider over it is the
// playhead: drag it, or use the arrow keys. The homepage and the explorer both use it.
export function YearStrip({
  firstNight,
  values,
  holidays,
  schoolHolidays = [],
  night,
  onSeek,
  labels = NO_LABELS,
  stay,
  ariaLabel,
  valueText,
}: Props) {
  const last = Math.max(1, values.length - 1)
  const shape = useMemo(() => {
    const top = Math.max(1e-9, ...values.map((v) => v ?? 0))
    const x = (n: number) => (n / last) * W
    const y = (v: number) => H - (v / top) * H * 0.92
    // A night with no value breaks the line, and the area dips to the floor there.
    let line = ''
    values.forEach((v, n) => {
      if (v === null) return
      line += `${n && values[n - 1] !== null ? 'L' : 'M'}${x(n).toFixed(1)},${y(v).toFixed(1)}`
    })
    const floor = values.map((v, n) => `${n ? 'L' : 'M'}${x(n).toFixed(1)},${y(v ?? 0).toFixed(1)}`)
    return { line, area: `${floor.join('')}L${W},${H}L0,${H}Z`, x }
  }, [values, last])
  const months = useMemo(() => monthStarts(firstNight, values.length), [firstNight, values.length])
  // Labels are spaced in pixels: on a phone, two that are weeks apart can touch.
  const box = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(0)
  useEffect(() => {
    if (!box.current) return
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width))
    observer.observe(box.current)
    return () => observer.disconnect()
  }, [])
  const placed = useMemo(
    () => placeLabels(labels, last, width, LABEL_CHAR_PX),
    [labels, last, width],
  )
  // Positions in the strip's box, matching the slider's thumb centre: see .year-strip in CSS.
  const at = (n: number) => `calc(var(--thumb) / 2 + ${n / last} * (100% - var(--thumb)))`

  return (
    <div className={placed.some((l) => l.row === 1) ? 'year-strip two-rows' : 'year-strip'} ref={box}>
      <ol className="year-peaks" aria-hidden="true">
        {placed.map((l) => (
          <li key={l.night} className={l.row === 1 ? 'row-1' : undefined} style={{ left: at(l.night) }}>
            {l.text}
          </li>
        ))}
      </ol>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" aria-hidden="true">
        {schoolHolidays.map((h) => (
          <rect
            key={`school-${h.night}`}
            className="year-school"
            x={shape.x(h.night)}
            width={Math.max(3, shape.x(h.night + h.nights) - shape.x(h.night))}
            y={0}
            height={H}
          />
        ))}
        {holidays.map((h) => (
          <rect
            key={h.night}
            className="year-holiday"
            x={shape.x(h.night)}
            width={Math.max(3, shape.x(h.night + h.nights) - shape.x(h.night))}
            y={0}
            height={H}
          />
        ))}
        {stay && (
          <rect
            className="year-stay"
            x={shape.x(stay.from)}
            width={Math.max(4, shape.x(stay.to) - shape.x(stay.from))}
            y={0}
            height={H}
          />
        )}
        <path className="year-area" d={shape.area} />
        <path className="year-line" d={shape.line} vectorEffect="non-scaling-stroke" />
      </svg>
      <input
        type="range"
        min={0}
        max={values.length - 1}
        value={night}
        onChange={(e) => onSeek(Number(e.target.value))}
        aria-label={ariaLabel}
        aria-valuetext={valueText(night)}
      />
      <ol className="year-months" aria-hidden="true">
        {months.map((m) => (
          <li key={m.night} style={{ left: at(m.night) }}>
            {m.month}
          </li>
        ))}
      </ol>
    </div>
  )
}
