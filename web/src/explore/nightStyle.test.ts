import type { LayerSpecification, StyleSpecification } from 'maplibre-gl'
import { describe, expect, it } from 'vitest'
import { nightStyle, type NightColours } from './nightStyle'

const COLOURS: NightColours = {
  land: 'land',
  park: 'park',
  built: 'built',
  sea: 'sea',
  road: 'road',
  label: 'label',
  halo: 'halo',
}

const style = (layers: LayerSpecification[]): StyleSpecification => ({
  version: 8,
  sources: {},
  layers,
})

const fill = (id: string): LayerSpecification => ({
  id,
  type: 'fill',
  source: 'openmaptiles',
  paint: { 'fill-color': 'rgb(12,12,12)', 'fill-outline-color': 'rgb(27,27,29)' },
})

const line = (id: string): LayerSpecification => ({
  id,
  type: 'line',
  source: 'openmaptiles',
  paint: { 'line-color': '#181818', 'line-width': 2 },
})

describe('nightStyle', () => {
  it('draws the land, sea and parks in the night colours', () => {
    const { layers } = nightStyle(
      style([
        { id: 'background', type: 'background', paint: { 'background-color': 'rgb(12,12,12)' } },
        fill('water'),
        fill('landuse_park'),
        fill('landcover_wood'),
        fill('building'),
      ]),
      COLOURS,
    )

    expect(layers.map((l) => l.paint && Object.values(l.paint)[0])).toEqual([
      'land',
      'sea',
      'park',
      'park',
      'built',
    ])
    // A fill's outline would draw the old grey round every shape.
    expect(layers[1].paint).not.toHaveProperty('fill-outline-color')
  })

  it('dims roads, and their casings more, keeping their widths', () => {
    const [minor, casing, waterway] = nightStyle(
      style([line('highway_minor'), line('highway_major_casing'), line('waterway')]),
      COLOURS,
    ).layers

    expect(minor.paint).toEqual({ 'line-color': 'road', 'line-opacity': 0.35, 'line-width': 2 })
    expect(casing.paint).toMatchObject({ 'line-color': 'road', 'line-opacity': 0.2 })
    expect(waterway.paint).toMatchObject({ 'line-color': 'sea' })
  })

  it('gives names the night label colour and halo', () => {
    const [town] = nightStyle(
      style([
        {
          id: 'place_town',
          type: 'symbol',
          source: 'openmaptiles',
          paint: { 'text-color': 'rgb(101,101,101)', 'text-halo-color': 'rgba(0,0,0,0.7)' },
        },
      ]),
      COLOURS,
    ).layers

    expect(town.paint).toEqual({ 'text-color': 'label', 'text-halo-color': 'halo' })
  })

  it('leaves layers it has no colour for as they are', () => {
    const unknown = [fill('something_new'), line('ferry'), { ...fill('x'), type: 'fill-extrusion' }]
    const oneway: LayerSpecification = { id: 'road_oneway', type: 'symbol', source: 'openmaptiles' }

    const { layers } = nightStyle(style([...unknown, oneway] as LayerSpecification[]), COLOURS)

    expect(layers).toEqual([...unknown, oneway])
  })

  it("doesn't need every layer: a style with no water is fine", () => {
    expect(nightStyle(style([line('highway_minor')]), COLOURS).layers).toHaveLength(1)
  })
})
