import { createContext, useContext, useEffect } from 'react'

// What a page is showing, for the night sounds: how busy (0 an ordinary stretch, 1 a busy one)
// and whether it's playing. A page that says nothing gets the quiet bed.
export type Scene = { swell: number; playing: boolean }
export const QUIET: Scene = { swell: 0, playing: true }

export type Switch = { on: boolean; supported: boolean; toggle: () => void }

// Two contexts: pages set the scene through a setter that never changes, so a page reporting
// twice a second doesn't re-render the ones that only listen to the switch, and vice versa.
export const SceneContext = createContext<(scene: Scene) => void>(() => undefined)
export const SwitchContext = createContext<Switch>({
  on: false,
  supported: false,
  toggle: () => undefined,
})

export function useSoundSwitch(): Switch {
  return useContext(SwitchContext)
}

// A page's scene while it's shown, and the quiet bed again when it goes.
export function useSoundScene(swell: number, playing = true) {
  const setScene = useContext(SceneContext)
  useEffect(() => {
    setScene({ swell, playing })
  }, [setScene, swell, playing])
  useEffect(() => () => setScene(QUIET), [setScene])
}
