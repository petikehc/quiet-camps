import { describe, expect, it } from 'vitest'
import { pageCounter, type GoatCounter } from './analytics'

function fakeGoat() {
  const counted: string[] = []
  const goat: GoatCounter = { count: ({ path }) => void counted.push(path) }
  return { goat, counted }
}

describe('pageCounter', () => {
  it('counts each path once the script is there', () => {
    const { goat, counted } = fakeGoat()
    const pages = pageCounter(() => goat)

    pages.count('/')
    pages.count('/explore')

    expect(counted).toEqual(['/', '/explore'])
  })

  it('keeps pages from before the script loaded, and counts them when it does', () => {
    const { goat, counted } = fakeGoat()
    let loaded: GoatCounter | undefined
    const pages = pageCounter(() => loaded)

    pages.count('/')
    expect(counted).toEqual([])

    loaded = goat
    pages.loaded()
    pages.loaded() // a second load event doesn't count them again

    expect(counted).toEqual(['/'])
  })

  it('waits while only settings are there, before the script adds count', () => {
    const { goat, counted } = fakeGoat()
    let loaded: Partial<GoatCounter> = {} // window.goatcounter = { allow_local: true }, say
    const pages = pageCounter(() => loaded)

    pages.count('/')
    loaded = goat
    pages.loaded()

    expect(counted).toEqual(['/'])
  })

  it('counts nothing if the script never loads (blocked)', () => {
    const pages = pageCounter(() => undefined)

    expect(() => {
      pages.count('/')
      pages.loaded()
    }).not.toThrow()
  })
})
