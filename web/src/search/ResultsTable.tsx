import { getRouteApi, Link } from '@tanstack/react-router'
import { createColumnHelper, tableFeatures, useTable } from '@tanstack/react-table'
import { useEffect, useRef } from 'react'
import type { components } from '../api/schema'
import { shownLocation } from './location'

export type QuietCampground = components['schemas']['QuietCampgroundOut']

// Module scope, so the table doesn't rebuild its models on every render. No sorting or
// filtering features: the API ranks and filters, and the table only lays out the rows.
const features = tableFeatures({})
const column = createColumnHelper<typeof features, QuietCampground>()
const columns = column.columns([
  column.accessor('name', {
    header: 'Campground',
    cell: (info) => (
      <>
        <CampgroundLink id={info.row.original.id} name={info.getValue()} />
        <LocationMark campground={info.row.original} />
      </>
    ),
  }),
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

const searchRoute = getRouteApi('/')

// Opens the campground's calendar on the year of the searched dates.
function CampgroundLink({ id, name }: { id: number; name: string }) {
  const { arrive } = searchRoute.useSearch()
  return (
    <Link
      to="/campgrounds/$campgroundId"
      params={{ campgroundId: String(id) }}
      search={{ year: Number(arrive.slice(0, 4)) }}
    >
      {name}
    </Link>
  )
}

// The same notes the map's pin shows on hover. Campers see "approx. location" for a park-centre
// dot; the review view marks every location that isn't exact with ⚠ and the reasons.
function LocationMark({ campground }: { campground: QuietCampground }) {
  const review = searchRoute.useSearch().review === 'locations'
  const { certainty, notes } = shownLocation(campground, review)
  if (certainty === 'exact') return null
  const text = notes.join('. ')
  if (!review) {
    return (
      <span className="location-mark" title={text}>
        {certainty === 'park' ? 'approx. location' : 'not on the map'}
      </span>
    )
  }
  return (
    <span className="location-mark" role="img" aria-label={`Location: ${text}`} title={text}>
      ⚠
    </span>
  )
}

type Props = {
  rows: QuietCampground[]
  selectedId: number | undefined
  onSelect: (id: number) => void
  scrollToSelected: boolean // true when the selection came from the map
}

export function ResultsTable({ rows, selectedId, onSelect, scrollToSelected }: Props) {
  const table = useTable({ features, columns, data: rows, getRowId: (row) => String(row.id) })
  const element = useRef<HTMLTableElement>(null)

  useEffect(() => {
    if (!scrollToSelected || selectedId === undefined) return
    element.current
      ?.querySelector(`tr[data-id="${selectedId}"]`)
      ?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }, [scrollToSelected, selectedId])

  return (
    <table className="results" ref={element}>
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
          <tr
            key={row.id}
            data-id={row.id}
            className={row.original.id === selectedId ? 'selected' : undefined}
            // A click on the row shows it on the map; the links in it still navigate.
            onClick={() => onSelect(row.original.id)}
          >
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
