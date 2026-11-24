import { useMemo, useState, type ReactNode } from 'react'
import { QUIET, SceneContext, SwitchContext, useSoundSwitch } from './scene'
import { useNightSounds } from './useNightSounds'

// Night sounds across the site: one switch in the header, off on every visit; the page in view
// says what they follow (useSoundScene).
export function NightSoundsProvider({ children }: { children: ReactNode }) {
  const [on, setOn] = useState(false)
  const [scene, setScene] = useState(QUIET)
  const { supported, unlock } = useNightSounds(on, scene.playing, scene.swell)
  const switched = useMemo(
    () => ({
      on,
      supported,
      toggle: () => {
        if (!on) unlock() // inside the click, as Safari needs
        setOn(!on)
      },
    }),
    [on, supported, unlock],
  )
  return (
    <SceneContext.Provider value={setScene}>
      <SwitchContext.Provider value={switched}>{children}</SwitchContext.Provider>
    </SceneContext.Provider>
  )
}

// The header's switch: a fixed label, so aria-pressed says whether it's on.
export function SoundSwitch() {
  const { on, supported, toggle } = useSoundSwitch()
  if (!supported) return null
  return (
    <button type="button" className="sound-switch" aria-pressed={on} onClick={toggle}>
      Night sounds
    </button>
  )
}
