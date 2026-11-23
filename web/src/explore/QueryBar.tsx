import { useDeferredValue, useState, type FormEvent } from 'react'
import { failedWords, filtersFrom, missedWords, useAsk } from './ask'
import { KM_CHOICES, type Filters } from './filters'
import { usePlaces, type Place } from './queries'

type Props = {
  filters: Filters
  onChange: (filters: Filters) => void
}

// What to look for: plain words, read by /ask, or the dates and place set by hand. Plain words
// fill in the fields below them, so whatever /ask can't do, the fields still can.
export function QueryBar({ filters, onChange }: Props) {
  return (
    <div className="query-bar">
      <Ask filters={filters} onChange={onChange} />
      <div className="query-dates">
        <label>
          Arrive
          <input
            type="date"
            value={filters.arrive}
            onChange={(e) => e.target.value && onChange({ ...filters, arrive: e.target.value })}
          />
        </label>
        <label>
          Leave
          <input
            type="date"
            value={filters.depart}
            min={filters.arrive}
            onChange={(e) => e.target.value && onChange({ ...filters, depart: e.target.value })}
          />
        </label>
      </div>
      <PlaceField filters={filters} onChange={onChange} />
      {filters.park && (
        <p className="chip">
          In {filters.park}
          <button
            type="button"
            aria-label={`Any park, not just ${filters.park}`}
            onClick={() => onChange({ ...filters, park: undefined })}
          >
            ×
          </button>
        </p>
      )}
    </div>
  )
}

function Ask({ filters, onChange }: Props) {
  const [text, setText] = useState('')
  const [note, setNote] = useState<string>()
  const ask = useAsk(
    (answer) => {
      setNote(missedWords(answer)?.replace('on the map page', 'below'))
      onChange({ ...filters, ...filtersFrom(answer, filters) })
    },
    (error) => setNote(failedWords(error).replace('on the map', 'below')),
  )

  function submit(e: FormEvent) {
    e.preventDefault()
    if (text.trim().length >= 3) ask.mutate(text.trim())
  }

  return (
    <form className="ask" onSubmit={submit} role="search">
      <label htmlFor="ask-text">Where and when?</label>
      <div className="ask-row">
        <input
          id="ask-text"
          value={text}
          maxLength={200}
          placeholder="next weekend around the Sunshine Coast"
          onChange={(e) => setText(e.target.value)}
        />
        <button type="submit" disabled={ask.isPending}>
          {ask.isPending ? 'Reading…' : 'Go'}
        </button>
      </div>
      <p className="ask-note" aria-live="polite">
        {note}
      </p>
    </form>
  )
}

function PlaceField({ filters, onChange }: Props) {
  const [text, setText] = useState('')
  const deferred = useDeferredValue(text)
  const places = usePlaces(deferred)

  function pick(place: Place) {
    setText('')
    onChange({ ...filters, near: place.name, lat: place.lat, lon: place.lon, km: filters.km ?? 50 })
  }

  if (filters.near !== undefined) {
    return (
      <div className="place-chosen">
        <span>Within</span>
        <select
          aria-label="How far"
          value={filters.km}
          onChange={(e) => onChange({ ...filters, km: Number(e.target.value) })}
        >
          {[...new Set([...KM_CHOICES, filters.km ?? 50])]
            .sort((a, b) => a - b)
            .map((km) => (
              <option key={km} value={km}>
                {km} km
              </option>
            ))}
        </select>
        <span>
          of <strong>{filters.near}</strong>
        </span>
        <button
          type="button"
          className="link-button"
          onClick={() =>
            onChange({ ...filters, near: undefined, lat: undefined, lon: undefined, km: undefined })
          }
        >
          Anywhere
        </button>
      </div>
    )
  }

  const found = deferred.trim().length >= 2 ? (places.data?.results ?? []) : []
  return (
    <div className="place-field">
      <label htmlFor="place-text">Near a town or park</label>
      <input
        id="place-text"
        value={text}
        placeholder="Noosa, Toowoomba, Main Range…"
        autoComplete="off"
        onChange={(e) => setText(e.target.value)}
      />
      {found.length > 0 && (
        <ul className="place-options">
          {found.map((p) => (
            <li key={`${p.kind}-${p.name}-${p.lat}`}>
              <button type="button" onClick={() => pick(p)}>
                {p.name} <span className="muted">{KIND_NAMES[p.kind] ?? p.kind}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

const KIND_NAMES: Record<string, string> = {
  council: 'council area',
  locality: 'town or suburb',
  park: 'park',
  campground: 'campground',
}
