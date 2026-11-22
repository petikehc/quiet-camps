import { useSyncExternalStore } from 'react'

const query = window.matchMedia('(prefers-color-scheme: dark)')

// useSyncExternalStore: React's hook for reading something it doesn't own (here, the OS theme)
// and re-rendering when it changes.
export function useDarkMode(): boolean {
  return useSyncExternalStore(
    (onChange) => {
      query.addEventListener('change', onChange)
      return () => query.removeEventListener('change', onChange)
    },
    () => query.matches,
  )
}
