import { describe, expect, it } from 'vitest'
import { startAt } from './starts'

describe('startAt', () => {
  it('starts from where you are, 150 km round', () => {
    expect(startAt(-27.47, 153.02)).toEqual({ near: 'your location', lat: -27.47, lon: 153.02, km: 150 })
  })

  it("can't start from somewhere the search won't take", () => {
    expect(startAt(51.5, -0.12)).toBeUndefined() // London
    expect(startAt(-8.5, 147.2)).toBeUndefined() // Port Moresby, north of -9
  })
})
