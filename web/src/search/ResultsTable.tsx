import { Link } from '@tanstack/react-router'
import { createColumnHelper, tableFeatures, useTable } from '@tanstack/react-table'
import type { components } from '../api/schema'

export type QuietCampground = components['schemas']['QuietCampgroundOut']

// Module scope, so the table doesn't rebuild its models on every render. No sorting or
// filtering features: the API ranks and filters, and the table only lays out the rows.
const features = tableFeatures({})
const column = createColumnHelper<typeof features, QuietCampground>()
const columns = column.columns([
  column.accessor('name', { header: 'Campground' }),
  column.accessor('park_name', {
    header: 'Park',
    cell: (info) => (
      <Link from="/" to="/" search={(prev) => ({ ...prev, park: info.getValue() })}>
        {info.getValue()}
      </Link>
    ),
  }),
  column.accessor('busyness', {
    header: 'Usually',
    cell: (info) => `${Math.round(info.getValue() * 100)}%`,
  }),
  column.accessor('typical_sites', {
    header: 'Sites booked',
    cell: (info) => Math.round(info.getValue()),
  }),
  column.accessor('history', { header: 'Nights of history' }),
])

export function ResultsTable({ rows }: { rows: QuietCampground[] }) {
  const table = useTable({ features, columns, data: rows, getRowId: (row) => String(row.id) })

  return (
    <table className="results">
      <caption>
        Quietest first. <strong>Usually</strong> is how busy a campground typically is on these
        nights, against its own busiest nights (100%). <strong>Sites booked</strong> is how many
        of its sites are typically booked on one of these nights, on average.
      </caption>
      <thead>
        {table.getHeaderGroups().map((group) => (
          <tr key={group.id}>
            {group.headers.map((header) => (
              <th key={header.id} scope="col">
                <table.FlexRender header={header} />
              </th>
            ))}
          </tr>
        ))}
      </thead>
      <tbody>
        {table.getRowModel().rows.map((row) => (
          <tr key={row.id}>
            {row.getAllCells().map((cell) => (
              <td key={cell.id}>
                <table.FlexRender cell={cell} />
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  )
}
