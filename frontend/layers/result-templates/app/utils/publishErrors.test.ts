import { describe, expect, it } from 'vitest'
import { describeResultTemplatePublishErrors } from './publishErrors'

const names = {
  templateAnalyte: (id: string) => ({ ta1: 'Glucosa (GLU)', ta2: 'VIH (HIV)' } as Record<string, string>)[id] ?? id,
  reference: (field: string, id: string) => `${field}:${id}`
}

describe('describeResultTemplatePublishErrors', () => {
  it('sin details reconocibles devuelve una lista vacía', () => {
    expect(describeResultTemplatePublishErrors(null, names)).toEqual([])
    expect(describeResultTemplatePublishErrors({ otra: 1 }, names)).toEqual([])
  })

  it('describe en español los campos faltantes por analito', () => {
    const lines = describeResultTemplatePublishErrors({
      missing: [
        { template_analyte_id: 'ta1', result_type: 'numeric', missing_fields: ['unit_id', 'decimals', 'reference_ranges'] }
      ],
      inactive: []
    }, names)
    expect(lines).toEqual([
      'Glucosa (GLU) (Numérico): falta unidad, decimales y al menos un rango de referencia activo.'
    ])
  })

  it('incluye los rangos incompatibles con el tipo de resultado', () => {
    const lines = describeResultTemplatePublishErrors({
      missing: [
        { template_analyte_id: 'ta2', result_type: 'qualitative', missing_fields: [], incompatible_reference_range_ids: ['r1', 'r2'] }
      ]
    }, names)
    expect(lines).toEqual([
      'VIH (HIV) (Cualitativo): 2 rangos de referencia usan campos que su tipo de resultado no admite.'
    ])
  })

  it('combina faltantes e incompatibles en una línea', () => {
    const lines = describeResultTemplatePublishErrors({
      missing: [
        { template_analyte_id: 'ta2', result_type: 'qualitative', missing_fields: ['option_set_id'], incompatible_reference_range_ids: ['r1'] }
      ]
    }, names)
    expect(lines).toEqual([
      'VIH (HIV) (Cualitativo): falta conjunto de opciones; 1 rango de referencia usa campos que su tipo de resultado no admite.'
    ])
  })

  it('describe las referencias inactivas con su nombre', () => {
    const lines = describeResultTemplatePublishErrors({
      missing: [],
      inactive: [
        { template_analyte_id: 'ta1', field: 'unit_id', id: 'u1' },
        { template_analyte_id: 'ta2', field: 'expected_option_id', id: 'o1' }
      ]
    }, names)
    expect(lines).toEqual([
      'Glucosa (GLU): la unidad «unit_id:u1» está inactiva.',
      'VIH (HIV): la opción esperada de un rango «expected_option_id:o1» está inactiva.'
    ])
  })

  it('un campo faltante o inactivo desconocido se muestra tal cual', () => {
    const lines = describeResultTemplatePublishErrors({
      missing: [{ template_analyte_id: 'ta1', result_type: 'numeric', missing_fields: ['nuevo_campo'] }],
      inactive: [{ template_analyte_id: 'ta1', field: 'otro_id', id: 'x' }]
    }, names)
    expect(lines).toEqual([
      'Glucosa (GLU) (Numérico): falta nuevo_campo.',
      'Glucosa (GLU): otro_id «otro_id:x» está inactivo.'
    ])
  })

  it('describe las fórmulas inválidas por analito, según el motivo', () => {
    const lines = describeResultTemplatePublishErrors({
      missing: [],
      inactive: [],
      invalid_formula: [
        { template_analyte_id: 'ta1', reason: 'unknown_code', message: 'x', codes: ['ZZ'] },
        { template_analyte_id: 'ta1', reason: 'cycle', message: 'y', codes: ['GLU', 'HDL', 'GLU'] },
        { template_analyte_id: 'ta2', reason: 'syntax', message: 'Sintaxis inválida: falta un operando.', codes: [] }
      ]
    }, names)
    expect(lines).toEqual([
      'Glucosa (GLU): fórmula inválida. Códigos que no son analitos de esta versión: ZZ.',
      'Glucosa (GLU): fórmula inválida. Referencia circular: GLU → HDL → GLU.',
      'VIH (HIV): fórmula inválida. Sintaxis inválida: falta un operando.'
    ])
  })

  it('invalid_formula vacía no agrega líneas', () => {
    expect(describeResultTemplatePublishErrors({ missing: [], inactive: [], invalid_formula: [] }, names)).toEqual([])
  })
})
