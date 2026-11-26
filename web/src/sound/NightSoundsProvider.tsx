import { useMemo, useState, type ReactNode } from 'react'
import { countEvent } from '../analytics'
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
        if (!on) {
          unlock() // inside the click, as Safari needs
          countEvent('sounds: on')
        }
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
      <SpeakerIcon on={on} />
      Night sounds
    </button>
  )
}

// A speaker: with sound waves when on, crossed out when off.
function SpeakerIcon({ on }: { on: boolean }) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 9h4l5-4v14l-5-4H4z" fill="currentColor" />
      <g fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        {on ? (
          <>
            <path d="M16.5 9a4 4 0 0 1 0 6" />
            <path d="M19 6.5a7.5 7.5 0 0 1 0 11" />
          </>
        ) : (
          <path d="M16.5 9.5l5 5m0-5l-5 5" />
        )}
      </g>
    </svg>
  )
}
