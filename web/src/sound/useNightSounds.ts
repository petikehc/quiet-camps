import { useCallback, useEffect, useRef, useState } from 'react'
import { NightSounds } from './sound'

const SUPPORTED = typeof window !== 'undefined' && 'AudioContext' in window

// Night sounds while they're on, the year is playing and the tab is in view; faded out and
// suspended otherwise, and closed when the page goes. `unlock` is for the switching-on click.
export function useNightSounds(on: boolean, playing: boolean, swell: number) {
  const sounds = useRef<NightSounds>(undefined)
  const [hidden, setHidden] = useState(() => document.hidden)

  useEffect(() => {
    const seen = () => setHidden(document.hidden)
    document.addEventListener('visibilitychange', seen)
    return () => document.removeEventListener('visibilitychange', seen)
  }, [])
  useEffect(() => () => sounds.current?.close(), [])

  const audible = on && playing && !hidden
  useEffect(() => {
    if (audible) void sounds.current?.start()
    else sounds.current?.stop()
  }, [audible])
  useEffect(() => {
    sounds.current?.setSwell(swell)
  }, [swell])

  const latestSwell = useRef(swell)
  useEffect(() => {
    latestSwell.current = swell
  }, [swell])
  const unlock = useCallback(() => {
    sounds.current ??= new NightSounds()
    sounds.current.setSwell(latestSwell.current)
    sounds.current.unlock()
  }, [])
  return { supported: SUPPORTED, unlock }
}
