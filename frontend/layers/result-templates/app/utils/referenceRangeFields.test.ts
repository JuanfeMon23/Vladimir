import { describe, expect, it } from 'vitest'
import { CATALOG_FIXTURES } from '~/testing/catalogs'
import { resultTemplateRangeFields, pickResultTemplateRangeValues } from './referenceRangeFields'

/** Banderas de un tipo de resultado sembrado (el backend las sirve en `/catalogs/result-types`). */
function behaviorOf(code: string) {
  return CATALOG_FIXTURES['result-types'].find(item => item.code === code)
}

describe('resultTemplateRangeFields', () => {
  it('numérico y calculado: límites normales y críticos', () => {
    const numeric = ['low', 'high', 'critical_low', 'critical_high']
    expect(resultTemplateRangeFields(behaviorOf('numeric'))).toEqual(numeric)
    expect(resultTemplateRangeFields(behaviorOf('calculated'))).toEqual(numeric)
  })

  it('cualitativo, semicuantitativo y título: opción esperada', () => {
    expect(resultTemplateRangeFields(behaviorOf('qualitative'))).toEqual(['expected_option_id'])
    expect(resultTemplateRangeFields(behaviorOf('semi_quantitative'))).toEqual(['expected_option_id'])
    expect(resultTemplateRangeFields(behaviorOf('titer'))).toEqual(['expected_option_id'])
  })

  it('booleano: valor esperado', () => {
    expect(resultTemplateRangeFields(behaviorOf('boolean'))).toEqual(['expected_boolean'])
  })

  it('texto: ningún campo tipado (solo texto a mostrar e interpretación)', () => {
    expect(resultTemplateRangeFields(behaviorOf('text'))).toEqual([])
  })
})

describe('resultTemplateRangeFields por banderas', () => {
  it('lo que admite sale de las banderas del catálogo, no del código del tipo', () => {
    const flags = { uses_numeric_range: false, uses_option_set: true, uses_boolean_range: true }
    expect(resultTemplateRangeFields(flags)).toEqual(['expected_option_id', 'expected_boolean'])
    expect(resultTemplateRangeFields({ ...flags, uses_numeric_range: true })).toEqual([
      'low', 'high', 'critical_low', 'critical_high', 'expected_option_id', 'expected_boolean'
    ])
  })

  it('un tipo desconocido (catálogo sin cargar) no admite campos tipados', () => {
    expect(resultTemplateRangeFields(undefined)).toEqual([])
    expect(pickResultTemplateRangeValues({ low: 1, display_text: 'x' }, undefined)).toEqual({ display_text: 'x' })
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
    expect(pickResultTemplateRangeValues(values, behaviorOf('numeric'))).toEqual({
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
    const result = pickResultTemplateRangeValues(values, behaviorOf('boolean'))
    expect(result).toHaveProperty('expected_boolean', true)
    expect(result).not.toHaveProperty('low')
    expect(result).not.toHaveProperty('expected_option_id')
  })

  it('título solo conserva la opción esperada (low/high/críticos/booleano darían 422 not_allowed)', () => {
    const result = pickResultTemplateRangeValues(values, behaviorOf('titer'))
    expect(result).toHaveProperty('expected_option_id', 'opt-1')
    for (const field of ['low', 'high', 'critical_low', 'critical_high', 'expected_boolean']) {
      expect(result).not.toHaveProperty(field)
    }
    expect(result).toHaveProperty('display_text', '70 - 110 mg/dL')
  })

  it('texto no envía ningún campo tipado', () => {
    const result = pickResultTemplateRangeValues(values, behaviorOf('text'))
    for (const field of ['low', 'high', 'critical_low', 'critical_high', 'expected_option_id', 'expected_boolean']) {
      expect(result).not.toHaveProperty(field)
    }
    expect(result).toHaveProperty('display_text', '70 - 110 mg/dL')
  })
})
