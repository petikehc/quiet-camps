import type { components } from '../api/schema'
import { formatNight, heatBin, holidayName } from '../charts/scales'

type LeadTime = components['schemas']['LeadTimeOut']

// A heat table, not a line chart: a campground can have ten kinds of night, too many lines
// to tell apart, and every value is printed, so the table is its own accessible view.
export function LeadTimeTable({ leadTime }: { leadTime: LeadTime }) {
  const [first] = leadTime.groups
  if (!first || !leadTime.since || !leadTime.until) {
    return <p>No bookings in the last three years.</p>
  }
  // Furthest first, so a row reads left to right as the night gets closer. 0 weeks is 100%.
  const weeks = first.booked_by.map((b) => b.weeks).filter((w) => w > 0).reverse()

  return (
    <table className="data-table lead-time">
      <caption>
        Share of booked nights already booked this many weeks before, for nights from{' '}
        {formatNight(leadTime.since)} to {formatNight(leadTime.until)}.
      </caption>
      <thead>
        <tr>
          <th scope="col">Night</th>
          {weeks.map((w) => (
            <th key={w} scope="col">
              {w} {w === 1 ? 'week' : 'weeks'}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {leadTime.groups.map((group) => (
          <tr key={group.group}>
            <th scope="row">
              {holidayName(group.group)} <span className="muted">{group.nights.toLocaleString()} nights</span>
            </th>
            {weeks.map((w) => {
              const share = group.booked_by.find((b) => b.weeks === w)?.share ?? 0
              const bin = heatBin(share)
              return (
                <td key={w} style={{ background: `var(--heat-${bin})`, color: `var(--heat-ink-${bin})` }}>
                  {Math.round(share * 100)}%
                </td>
              )
            })}
          </tr>
        ))}
      </tbody>
    </table>
  )
}
