import { useMutation } from '@tanstack/react-query'
import { api } from '../api/client'
import type { components } from '../api/schema'
import { ApiError, unwrap } from '../api/errors'
import type { Filters } from './filters'

export type Answer = components['schemas']['AskOut']

// What /ask understood, laid over the filters already set: whatever it didn't understand
// stays as it was.
export function filtersFrom(answer: Answer, filters: Partial<Filters> = {}): Partial<Filters> {
  const next: Partial<Filters> = { ...filters }
  if (answer.arrive && answer.depart) Object.assign(next, { arrive: answer.arrive, depart: answer.depart })
  if (answer.place) {
    Object.assign(next, {
      near: answer.place.name,
      lat: answer.place.lat,
      lon: answer.place.lon,
      km: answer.within_km ?? 50,
    })
  }
  return next
}

// What to tell someone when /ask couldn't understand everything, or couldn't be asked.
export function missedWords(answer: Answer): string | undefined {
  const missed = [
    !answer.arrive && 'the dates',
    !answer.place && answer.place_asked && `“${answer.place_asked}” in Queensland`,
  ].filter(Boolean)
  return missed.length ? `Couldn't find ${missed.join(' or ')}: set it on the map page.` : undefined
}

export function failedWords(error: Error): string {
  return error instanceof ApiError && error.status === 429
    ? "That's a lot of asking: try again in an hour, or pick dates and a place on the map."
    : "Plain words aren't working right now: pick dates and a place on the map."
}

// POST /ask, for the homepage's box and the explorer's.
export function useAsk(onAnswer: (answer: Answer) => void, onFail: (error: Error) => void) {
  return useMutation({
    mutationFn: (text: string) => unwrap(api.POST('/ask', { body: { text } })),
    onSuccess: onAnswer,
    onError: onFail,
  })
}
