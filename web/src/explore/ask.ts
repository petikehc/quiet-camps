import { useMutation } from '@tanstack/react-query'
import { countEvent } from '../analytics'
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
  return missed.length ? `Couldn't find ${missed.join(' or ')}: set it on the map.` : undefined
}

export function failedWords(error: Error): string {
  return error instanceof ApiError && error.status === 429
    ? "That's a lot of asking: try again in an hour, or pick dates and a place on the map."
    : "Plain words aren't working right now: pick dates and a place on the map."
}

// How an ask went, for GoatCounter: never the words, only whether they were understood or why
// they couldn't be asked. The API's daily cap is the 503 that says "tomorrow".
export function askOutcome(result: Answer | Error): string {
  if (result instanceof Error) {
    if (result instanceof ApiError && result.status === 429) return 'ask: hourly limit'
    const daily = result instanceof ApiError && result.problem?.detail.includes('tomorrow')
    return daily ? 'ask: daily cap' : 'ask: unavailable'
  }
  if (!result.arrive && !result.place) return 'ask: not understood'
  return missedWords(result) ? 'ask: partly' : 'ask: understood'
}

// POST /ask, for the homepage's box and the explorer's.
export function useAsk(onAnswer: (answer: Answer) => void, onFail: (error: Error) => void) {
  return useMutation({
    mutationFn: (text: string) => unwrap(api.POST('/ask', { body: { text } })),
    onSuccess: (answer) => {
      countEvent(askOutcome(answer))
      onAnswer(answer)
    },
    onError: (error) => {
      countEvent(askOutcome(error))
      onFail(error)
    },
  })
}
