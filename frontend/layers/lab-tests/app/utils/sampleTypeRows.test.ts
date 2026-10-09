import { describe, expect, it } from 'vitest'
import {
  LAB_TEST_NO_SAMPLE_TYPES_MESSAGE,
  LAB_TEST_PREFERRED_MESSAGE,
  emptySampleTypeRow,
  labTestSampleTypeRowsSchema,
  labTestSampleTypesPayload,
  preferSampleTypeRow,
  sampleTypeCatalogEntries
} from './sampleTypeRows'

const row = (id: string, over: Record<string, unknown> = {}) => ({ ...emptySampleTypeRow(id), ...over })

function messages(rows: unknown) {
  const result = labTestSampleTypeRowsSchema.safeParse(rows)
  return result.success ? [] : result.error.issues.map(issue => issue.message)
}

describe('labTestSampleTypeRowsSchema', () => {
  it('exige al menos un tipo marcado (también con la lista vacía)', () => {
    expect(messages([])).toEqual([LAB_TEST_NO_SAMPLE_TYPES_MESSAGE])
    expect(messages([row('a'), row('b')])).toEqual([LAB_TEST_NO_SAMPLE_TYPES_MESSAGE])
  })

  it('exige exactamente un preferido entre los marcados', () => {
    expect(messages([row('a', { selected: true })])).toEqual([LAB_TEST_PREFERRED_MESSAGE])
    expect(messages([
      row('a', { selected: true, is_preferred: true }),
      row('b', { selected: true, is_preferred: true })
    ])).toEqual([LAB_TEST_PREFERRED_MESSAGE])
  })

  it('valida con un marcado preferido; ignora lo no marcado', () => {
    expect(messages([row('a', { selected: true, is_preferred: true }), row('b', { is_preferred: true })])).toEqual([])
  })
})

describe('preferSampleTypeRow', () => {
  it('deja preferido solo el indicado', () => {
    const rows = [row('a', { is_preferred: true }), row('b'), row('c', { is_preferred: true })]
    expect(preferSampleTypeRow(rows, 2).map(r => r.is_preferred)).toEqual([false, false, true])
  })
})

describe('labTestSampleTypesPayload', () => {
  it('envía solo los marcados con sort_order = posición y el volumen numérico', () => {
    const parsed = labTestSampleTypeRowsSchema.parse([
      row('a'),
      row('b', { selected: true, is_preferred: true, required_volume_ml: '2.5' }),
      row('c', { selected: true })
    ])
    expect(labTestSampleTypesPayload(parsed)).toEqual([
      { sample_type_id: 'b', is_preferred: true, required_volume_ml: 2.5, sort_order: 1 },
      { sample_type_id: 'c', is_preferred: false, required_volume_ml: null, sort_order: 2 }
    ])
  })
})

describe('sampleTypeCatalogEntries', () => {
  it('un tipo es ofrecible si él y su muestra están activos', () => {
    const entries = sampleTypeCatalogEntries([
      { id: 's1', code: 'SAN', name: 'Sangre', is_active: true, types: [
        { id: 't1', code: 'SUE', name: 'Suero', is_active: true, specimen: 'serum' },
        { id: 't2', code: 'EDT', name: 'EDTA', is_active: false, specimen: 'serum' }
      ] },
      { id: 's2', code: 'ORI', name: 'Orina', is_active: false, types: [{ id: 't3', code: 'ORI', name: 'Orina', is_active: true, specimen: 'urine' }] }
    ])
    expect(entries).toEqual([
      { id: 't1', label: 'Suero (SUE · Sangre)', isActive: true },
      { id: 't2', label: 'EDTA (EDT · Sangre)', isActive: false },
      { id: 't3', label: 'Orina (ORI · Orina)', isActive: false }
    ])
  })
})
