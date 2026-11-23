import { describe, expect, it } from 'vitest'
import { ApiError } from '../api/errors'
import { failedWords, filtersFrom, missedWords, type Answer } from './ask'

const noosa = { name: 'Noosa', kind: 'council', lat: -26.32, lon: 152.93 }
const answer = (fields: Partial<Answer>): Answer => ({
  arrive: null,
  depart: null,
  place: null,
  place_asked: null,
  place_role: null,
  within_km: null,
  ...fields,
})

describe('filtersFrom', () => {
  it('takes the dates and the place understood', () => {
    const found = filtersFrom(
      answer({ arrive: '2027-03-25', depart: '2027-03-29', place: noosa, within_km: 50 }),
    )
    expect(found).toEqual({
      arrive: '2027-03-25',
      depart: '2027-03-29',
      near: 'Noosa',
      lat: -26.32,
      lon: 152.93,
      km: 50,
    })
  })

  it('keeps what was set when the words said nothing about it', () => {
    const set = { arrive: '2027-01-08', depart: '2027-01-10', park: 'Main Range National Park' }
    expect(filtersFrom(answer({ place: noosa }), set)).toMatchObject(set)
  })
})

describe('missedWords', () => {
  it('says what it could not find', () => {
    expect(missedWords(answer({ place_asked: 'Tweed Heads' }))).toBe(
      "Couldn't find the dates or “Tweed Heads” in Queensland: set it on the map page.",
    )
    expect(missedWords(answer({ arrive: '2027-03-25', depart: '2027-03-29', place: noosa }))).toBeUndefined()
  })
})

describe('failedWords', () => {
  it('tells too many asks from asking being off', () => {
    expect(failedWords(new ApiError(429, undefined))).toMatch(/try again in an hour/)
    expect(failedWords(new ApiError(503, undefined))).toMatch(/aren't working right now/)
  })
})
