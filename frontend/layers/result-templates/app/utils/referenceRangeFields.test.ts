import { describe, expect, it } from 'vitest'
import { resultTemplateRangeFields, pickResultTemplateRangeValues } from './referenceRangeFields'

describe('resultTemplateRangeFields', () => {
  it('numérico y calculado: límites normales y críticos', () => {
    const numeric = ['low', 'high', 'critical_low', 'critical_high']
    expect(resultTemplateRangeFields('numeric')).toEqual(numeric)
    expect(resultTemplateRangeFields('calculated')).toEqual(numeric)
  })

  it('cualitativo, semicuantitativo y título: opción esperada', () => {
    expect(resultTemplateRangeFields('qualitative')).toEqual(['expected_option_id'])
    expect(resultTemplateRangeFields('semi_quantitative')).toEqual(['expected_option_id'])
    expect(resultTemplateRangeFields('titer')).toEqual(['expected_option_id'])
  })

  it('booleano: valor esperado', () => {
    expect(resultTemplateRangeFields('boolean')).toEqual(['expected_boolean'])
  })

  it('texto: ningún campo tipado (solo texto a mostrar e interpretación)', () => {
    expect(resultTemplateRangeFields('text')).toEqual([])
  })
})

describe('pickResultTemplateRangeValues', () => {
  const values = {
    sex: 'any' as const,
    age_min: 18,
    age_max: null,
    age_unit: 'anos' as const,
    condition: null,
    low: 70,
    high: 110,
    critical_low: 40,
    critical_high: null,
    expected_option_id: 'opt-1',
    expected_boolean: true,
    display_text: '70 - 110 mg/dL',
    interpretation: null
  }

  it('quita (no envía) los campos tipados que el tipo no admite y deja los comunes', () => {
    expect(pickResultTemplateRangeValues(values, 'numeric')).toEqual({
      sex: 'any',
      age_min: 18,
      age_max: null,
      age_unit: 'anos',
      condition: null,
      low: 70,
      high: 110,
      critical_low: 40,
      critical_high: null,
      display_text: '70 - 110 mg/dL',
      interpretation: null
    })
  })

  it('booleano solo conserva expected_boolean entre los tipados', () => {
    const result = pickResultTemplateRangeValues(values, 'boolean')
    expect(result).toHaveProperty('expected_boolean', true)
    expect(result).not.toHaveProperty('low')
    expect(result).not.toHaveProperty('expected_option_id')
  })

  it('título solo conserva la opción esperada (low/high/críticos/booleano darían 422 not_allowed)', () => {
    const result = pickResultTemplateRangeValues(values, 'titer')
    expect(result).toHaveProperty('expected_option_id', 'opt-1')
    for (const field of ['low', 'high', 'critical_low', 'critical_high', 'expected_boolean']) {
      expect(result).not.toHaveProperty(field)
    }
    expect(result).toHaveProperty('display_text', '70 - 110 mg/dL')
  })

  it('texto no envía ningún campo tipado', () => {
    const result = pickResultTemplateRangeValues(values, 'text')
    for (const field of ['low', 'high', 'critical_low', 'critical_high', 'expected_option_id', 'expected_boolean']) {
      expect(result).not.toHaveProperty(field)
    }
    expect(result).toHaveProperty('display_text', '70 - 110 mg/dL')
  })
})
