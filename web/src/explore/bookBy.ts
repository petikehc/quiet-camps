import type { components } from '../api/schema'
import type { Holiday } from '../charts/dates'
import { addDays } from './filters'

export type LeadTime = components['schemas']['LeadTimeOut']
type BookedBy = components['schemas']['BookedByOut']

// Fewer booked nights than this behind a share, and it's too rough to say.
const ENOUGH_NIGHTS = 10

export type BookBy = {
  group: string // the kind of night: a holiday, "weekend" or "weeknight"
  weeks: number // half its bookings for that kind of night are made this many weeks ahead
  date: string // so for these nights, by this day
}

// The kind of night the lead-time groups use: the holiday the arrival falls in, else a weekend
// (Friday or Saturday night) or a weeknight.
export function groupFor(arrive: string, holiday: Holiday | undefined): string {
  if (holiday) return holiday.name
  const weekday = new Date(`${arrive}T00:00:00Z`).getUTCDay()
  return weekday === 5 || weekday === 6 ? 'weekend' : 'weeknight'
}

// How many weeks ahead half the bookings were made: where the share booked crosses one half,
// in a straight line between the weeks measured (0, 1, 2, 4, 8, 13, 26, 52).
export function halfBookedWeeks(bookedBy: BookedBy[]): number {
  const points = [...bookedBy].sort((a, b) => a.weeks - b.weeks)
  for (let i = 0; i + 1 < points.length; i++) {
    const [near, far] = [points[i], points[i + 1]]
    if (near.share >= 0.5 && far.share < 0.5) {
      return near.weeks + ((near.share - 0.5) / (near.share - far.share)) * (far.weeks - near.weeks)
    }
  }
  return points.at(-1)?.weeks ?? 0 // half or more booked a year ahead
}

export function bookBy(lead: LeadTime, arrive: string, holiday: Holiday | undefined): BookBy | undefined {
  const group = groupFor(arrive, holiday)
  const found = lead.groups.find((g) => g.group === group)
  if (!found || found.nights < ENOUGH_NIGHTS) return undefined
  const weeks = halfBookedWeeks(found.booked_by)
  return { group, weeks, date: addDays(arrive, -Math.round(weeks * 7)) }
}
