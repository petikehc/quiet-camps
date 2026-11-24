// Night sounds for the homepage, off until switched on: a cricket chorus always, crickets by the
// sea swelling in on busy stretches, and a quiet campfire. Recordings in public/sounds
// (CREDITS.md). Every change is smoothed over seconds, so nothing jumps.

const LAYERS = ['night', 'night-busy', 'campfire'] as const
const BED = 0.45 // the cricket chorus, always
const BUSY = 0.6 // the busy chorus at full swell
const FIRE = [0.12, 0.3] // the campfire, from a quiet stretch to a busy one
const FADE = 0.35 // seconds: the time constant of a fade in or out
const DRIFT = 2 // seconds: the time constant of the swell
const SUSPEND_AFTER = 1500 // ms after a fade out, when it's silent

type Fetch = (url: string) => Promise<Response>

export class NightSounds {
  private context?: AudioContext
  private master?: GainNode
  private gains?: Record<(typeof LAYERS)[number], GainNode>
  private loading?: Promise<void>
  private swell = 0
  private suspendTimer?: ReturnType<typeof setTimeout>

  private readonly base: string
  private readonly makeContext: () => AudioContext
  private readonly fetcher: Fetch

  constructor(
    base = `${import.meta.env.BASE_URL}sounds/`,
    makeContext: () => AudioContext = () => new AudioContext(),
    fetcher: Fetch = (url) => fetch(url),
  ) {
    this.base = base
    this.makeContext = makeContext
    this.fetcher = fetcher
  }

  // Called in the click that switches sound on: some browsers (Safari) only let audio start in
  // the handler of a user's gesture.
  unlock(): void {
    this.context ??= this.makeContext()
    void this.context.resume()
  }

  async start(): Promise<void> {
    this.unlock()
    const context = this.context!
    clearTimeout(this.suspendTimer)
    await context.resume()
    this.loading ??= this.load(context)
    await this.loading
    this.master!.gain.setTargetAtTime(1, context.currentTime, FADE)
  }

  stop(): void {
    const context = this.context
    if (!context || !this.master) return
    this.master.gain.setTargetAtTime(0, context.currentTime, FADE)
    clearTimeout(this.suspendTimer)
    this.suspendTimer = setTimeout(() => void context.suspend(), SUSPEND_AFTER)
  }

  setSwell(swell: number): void {
    this.swell = swell
    const context = this.context
    if (!context || !this.gains) return
    const at = context.currentTime
    this.gains['night-busy'].gain.setTargetAtTime(BUSY * swell, at, DRIFT)
    this.gains.campfire.gain.setTargetAtTime(FIRE[0] + (FIRE[1] - FIRE[0]) * swell, at, DRIFT)
  }

  close(): void {
    clearTimeout(this.suspendTimer)
    void this.context?.close()
    this.context = undefined
  }

  // Fetches and decodes the loops, and starts them looping, silent until the master fades in.
  private async load(context: AudioContext): Promise<void> {
    this.master = context.createGain()
    this.master.gain.value = 0
    this.master.connect(context.destination)
    const buffers = await Promise.all(
      LAYERS.map(async (name) => {
        const response = await this.fetcher(`${this.base}${name}.m4a`)
        return context.decodeAudioData(await response.arrayBuffer())
      }),
    )
    const gains = {} as Record<(typeof LAYERS)[number], GainNode>
    LAYERS.forEach((name, i) => {
      const gain = context.createGain()
      gain.connect(this.master!)
      const source = context.createBufferSource()
      source.buffer = buffers[i]
      source.loop = true
      source.connect(gain)
      source.start()
      gains[name] = gain
    })
    gains.night.gain.setTargetAtTime(BED, context.currentTime, FADE)
    this.gains = gains
    this.setSwell(this.swell)
  }
}
