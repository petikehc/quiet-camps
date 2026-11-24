import { useEffect, useRef, useState } from 'react'

const REDUCED_MOTION = window.matchMedia('(prefers-reduced-motion: reduce)').matches

// A number that eases to each new value over `ms` instead of jumping: the night's count changes
// four times a second while the year plays. With reduced motion it just changes.
export function useEased(target: number, ms = 220): number {
  const [shown, setShown] = useState(target)
  const current = useRef(target)
  useEffect(() => {
    if (REDUCED_MOTION) return
    const from = current.current
    const start = performance.now()
    let frame = requestAnimationFrame(function step(now) {
      const t = Math.min(1, (now - start) / ms)
      current.current = from + (target - from) * (1 - (1 - t) ** 3) // ease out
      setShown(current.current)
      if (t < 1) frame = requestAnimationFrame(step)
    })
    return () => cancelAnimationFrame(frame)
  }, [target, ms])
  return REDUCED_MOTION ? target : shown
}
