import { describe, expect, it } from 'vitest'
import { counter, linkEvent, type Count, type GoatCounter } from './analytics'

function fakeGoat() {
  const counted: Count[] = []
  const goat: GoatCounter = { count: (vars) => void counted.push(vars) }
  return { goat, counted }
}

const paths = (counted: Count[]) => counted.map((c) => c.path)

describe('counter', () => {
  it('counts each path once the script is there', () => {
    const { goat, counted } = fakeGoat()
    const counts = counter(() => goat)

    counts.count({ path: '/' })
    counts.count({ path: '/explore' })

    expect(paths(counted)).toEqual(['/', '/explore'])
  })

  it('keeps counts from before the script loaded, and sends them when it does', () => {
    const { goat, counted } = fakeGoat()
    let loaded: GoatCounter | undefined
    const counts = counter(() => loaded)

    counts.count({ path: '/' })
    counts.count({ path: 'sounds: on', event: true })
    expect(counted).toEqual([])

    loaded = goat
    counts.loaded()
    counts.loaded() // a second load event doesn't count them again

    expect(counted).toEqual([{ path: '/' }, { path: 'sounds: on', event: true }])
  })

  it('waits while only settings are there, before the script adds count', () => {
    const { goat, counted } = fakeGoat()
    let loaded: Partial<GoatCounter> = {} // window.goatcounter = { allow_local: true }, say
    const counts = counter(() => loaded)

    counts.count({ path: '/' })
    loaded = goat
    counts.loaded()

    expect(paths(counted)).toEqual(['/'])
  })

  it('counts nothing if the script never loads (blocked)', () => {
    const counts = counter(() => undefined)

    expect(() => {
      counts.count({ path: '/' })
      counts.loaded()
    }).not.toThrow()
  })
})

describe('linkEvent', () => {
  const site = 'https://quiet-camps.idoescode.com'

  it('names an internal link by where it goes and what it says', () => {
    expect(linkEvent(`${site}/explore`, ' Or browse  the map ', site)).toBe(
      'link: /explore · Or browse the map',
    )
  })

  it('leaves out the search: it can hold dates and a place', () => {
    expect(linkEvent(`${site}/explore?arrive=2027-03-25&near=Noosa`, 'Map', site)).toBe(
      'link: /explore · Map',
    )
    const finder = 'https://parks.qld.gov.au/parks?q=Main+Range'
    expect(linkEvent(finder, 'Find the park on QPWS', site)).toBe(
      'out: parks.qld.gov.au/parks · Find the park on QPWS',
    )
  })

  it('names an external link by its host and path', () => {
    expect(
      linkEvent(
        'https://parks.qld.gov.au/parks/main-range/camping/quiet-creek',
        'Camping area on QPWS',
        site,
      ),
    ).toBe('out: parks.qld.gov.au/parks/main-range/camping/quiet-creek · Camping area on QPWS')
  })

  it('shortens long text', () => {
    const name = linkEvent(`${site}/campgrounds/1`, 'x'.repeat(100), site)

    expect(name).toBe(`link: /campgrounds/1 · ${'x'.repeat(59)}…`)
  })

  it('names a link with no text by where it goes alone', () => {
    expect(linkEvent(`${site}/`, '', site)).toBe('link: /')
  })

  it('ignores anchors that go nowhere', () => {
    expect(linkEvent(`${site}/explore#cards`, 'Skip to the list', site)).toBeUndefined()
    expect(linkEvent('mailto:someone@example.com', 'Email', site)).toBeUndefined()
    expect(linkEvent('javascript:void(0)', 'Nothing', site)).toBeUndefined()
  })
})
