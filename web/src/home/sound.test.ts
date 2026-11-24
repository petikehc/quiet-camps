import { afterEach, describe, expect, it, vi } from 'vitest'
import { NightSounds } from './sound'

// Just enough of the Web Audio API to see what NightSounds asks of it.
class FakeParam {
  value = 0
  targets: number[] = []
  setTargetAtTime(value: number) {
    this.targets.push(value)
    this.value = value
  }
}

class FakeContext {
  state: 'running' | 'suspended' | 'closed' = 'suspended'
  currentTime = 0
  destination = {}
  gains: FakeParam[] = []
  started = 0
  createGain() {
    const gain = new FakeParam()
    this.gains.push(gain)
    return { gain, connect: () => undefined }
  }
  createBufferSource() {
    return { buffer: null, loop: false, connect: () => undefined, start: () => void this.started++ }
  }
  decodeAudioData = async () => ({})
  resume = async () => void (this.state = 'running')
  suspend = async () => void (this.state = 'suspended')
  close = async () => void (this.state = 'closed')
}

function make() {
  const context = new FakeContext()
  const fetched: string[] = []
  const fetcher = async (url: string) => {
    fetched.push(url)
    return { arrayBuffer: async () => new ArrayBuffer(8) } as Response
  }
  const sounds = new NightSounds('/sounds/', () => context as unknown as AudioContext, fetcher)
  return { sounds, context, fetched }
}

afterEach(() => {
  vi.useRealTimers()
})

describe('NightSounds', () => {
  it('fetches nothing until it is switched on', () => {
    const { fetched } = make()
    expect(fetched).toEqual([])
  })

  it('loads the three loops once, starts them, and fades in', async () => {
    const { sounds, context, fetched } = make()
    sounds.unlock()
    await sounds.start()
    await sounds.start() // a second start doesn't load or start them again

    expect(fetched).toEqual(['/sounds/night.m4a', '/sounds/night-busy.m4a', '/sounds/campfire.m4a'])
    expect(context.started).toBe(3)
    expect(context.state).toBe('running')
    expect(context.gains[0].value).toBeGreaterThan(0) // the master fades in
  })

  it('fades out and then suspends when stopped', async () => {
    vi.useFakeTimers()
    const { sounds, context } = make()
    sounds.unlock()
    await sounds.start()

    sounds.stop()
    expect(context.gains[0].value).toBe(0)
    await vi.runAllTimersAsync()
    expect(context.state).toBe('suspended')
  })

  it('swells the busy layer with the data', async () => {
    const { sounds, context } = make()
    sounds.unlock()
    await sounds.start()
    sounds.setSwell(0)
    const quiet = context.gains.map((g) => g.value)
    sounds.setSwell(1)
    const busy = context.gains.map((g) => g.value)

    expect(busy[2]).toBeGreaterThan(quiet[2]) // the busy chorus
    expect(busy[1]).toBe(quiet[1]) // the bed stays put
  })
})
