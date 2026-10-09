import { describe, expect, it } from 'vitest'
import { buildReportPreview, formatReferenceRange } from './reportPreview'
import type { ReferenceRangeRead, ResultTemplateAnalyteRead, ResultTemplateSectionRead } from '../types/result-templates'

function range(over: Partial<ReferenceRangeRead> = {}): ReferenceRangeRead {
  return {
    id: 'r1',
    template_analyte_id: 'ta1',
    sex: 'any',
    age_min: null,
    age_max: null,
    age_unit: null,
    condition: null,
    low: null,
    high: null,
    critical_low: null,
    critical_high: null,
    expected_option_id: null,
    expected_boolean: null,
    display_text: null,
    interpretation: null,
    is_active: true,
    created_at: '',
    updated_at: '',
    ...over
  }
}

const ctx = { unit: 'mg/dL', decimals: null as number | null, option: (id: string) => ({ o1: 'No reactivo' } as Record<string, string>)[id] ?? id }

describe('formatReferenceRange', () => {
  it('display_text tiene prioridad sobre los límites', () => {
    expect(formatReferenceRange(range({ display_text: '70 - 110 (ayuno)', low: 1, high: 2 }), ctx)).toBe('70 - 110 (ayuno)')
  })

  it('low y high: "low – high unidad"', () => {
    expect(formatReferenceRange(range({ low: 70, high: 110 }), ctx)).toBe('70 – 110 mg/dL')
  })

  it('solo low o solo high usan ≥ / ≤', () => {
    expect(formatReferenceRange(range({ low: 70 }), ctx)).toBe('≥ 70 mg/dL')
    expect(formatReferenceRange(range({ high: 110 }), ctx)).toBe('≤ 110 mg/dL')
  })

  it('formatea con los decimales del analito', () => {
    expect(formatReferenceRange(range({ low: 3.5, high: 5 }), { ...ctx, unit: 'mmol/L', decimals: 2 })).toBe('3.50 – 5.00 mmol/L')
  })

  it('sin unidad no deja espacios sobrantes', () => {
    expect(formatReferenceRange(range({ low: 1, high: 2 }), { ...ctx, unit: null })).toBe('1 – 2')
  })

  it('opción esperada y booleano esperado', () => {
    expect(formatReferenceRange(range({ expected_option_id: 'o1' }), ctx)).toBe('Esperado: No reactivo')
    expect(formatReferenceRange(range({ expected_boolean: true }), ctx)).toBe('Esperado: Sí')
    expect(formatReferenceRange(range({ expected_boolean: false }), ctx)).toBe('Esperado: No')
  })

  it('agrega los valores críticos', () => {
    expect(formatReferenceRange(range({ low: 70, high: 110, critical_low: 40, critical_high: 400 }), ctx))
      .toBe('70 – 110 mg/dL · Crítico: < 40 mg/dL, > 400 mg/dL')
  })

  it('antepone sexo, edad y condición, y añade la interpretación', () => {
    const text = formatReferenceRange(range({
      sex: 'female', age_min: 18, age_max: 65, age_unit: 'anos', condition: 'Embarazo', low: 12, high: 16, interpretation: 'Normal'
    }), { ...ctx, unit: 'g/dL' })
    expect(text).toBe('Femenino · 18–65 años · Embarazo: 12 – 16 g/dL (Normal)')
  })

  it('edad con un solo límite', () => {
    expect(formatReferenceRange(range({ age_min: 65, age_unit: 'anos', low: 1, high: 2 }), ctx)).toBe('≥ 65 años: 1 – 2 mg/dL')
    expect(formatReferenceRange(range({ age_max: 12, age_unit: 'meses', low: 1, high: 2 }), ctx)).toBe('≤ 12 meses: 1 – 2 mg/dL')
  })

  it('un rango sin valores devuelve "Sin valores definidos"', () => {
    expect(formatReferenceRange(range(), ctx)).toBe('Sin valores definidos')
  })
})

function section(id: string, name: string, sort_order: number, is_active = true): ResultTemplateSectionRead {
  return { id, name, sort_order, is_active } as ResultTemplateSectionRead
}
function analyte(id: string, over: Partial<ResultTemplateAnalyteRead> = {}): ResultTemplateAnalyteRead {
  return {
    id,
    analyte_id: `an-${id}`,
    section_id: null,
    sort_order: 0,
    result_type: 'numeric',
    unit_id: 'u1',
    decimals: 1,
    is_required: true,
    is_reportable: true,
    is_active: true,
    ...over
  } as ResultTemplateAnalyteRead
}

const names = {
  analyte: (id: string) => `Nombre ${id}`,
  unit: (id: string | null) => (id === 'u1' ? 'mg/dL' : null),
  option: (id: string) => id
}

describe('buildReportPreview', () => {
  it('ordena secciones y analitos, agrupa el resto en "Sin sección" y deja fuera los inactivos', () => {
    const preview = buildReportPreview({
      sections: [section('s2', 'Bioquímica', 2), section('s1', 'Hematología', 1), section('s3', 'Vieja', 3, false)],
      analytes: [
        analyte('a1', { section_id: 's2', sort_order: 2 }),
        analyte('a2', { section_id: 's2', sort_order: 1 }),
        analyte('a3', { section_id: 's1' }),
        analyte('a4', { section_id: null }),
        analyte('a5', { section_id: 's3' }),
        analyte('a6', { section_id: 's1', is_active: false })
      ],
      ranges: {},
      names
    })
    expect(preview.map(group => [group.name, group.rows.map(row => row.id)])).toEqual([
      ['Hematología', ['a3']],
      ['Bioquímica', ['a2', 'a1']],
      ['Sin sección', ['a4', 'a5']]
    ])
  })

  it('la fila trae nombre, tipo, unidad, decimales y solo los rangos activos formateados', () => {
    const [group] = buildReportPreview({
      sections: [],
      analytes: [analyte('a1', { is_reportable: false })],
      ranges: {
        a1: [
          range({ id: 'r1', template_analyte_id: 'a1', low: 70, high: 110 }),
          range({ id: 'r2', template_analyte_id: 'a1', low: 1, high: 2, is_active: false })
        ]
      },
      names
    })
    expect(group!.rows).toEqual([{
      id: 'a1',
      name: 'Nombre an-a1',
      resultType: 'Numérico',
      unit: 'mg/dL',
      decimals: 1,
      required: true,
      reportable: false,
      ranges: ['70.0 – 110.0 mg/dL']
    }])
  })

  it('sin analitos activos no hay grupos', () => {
    expect(buildReportPreview({ sections: [section('s1', 'X', 1)], analytes: [], ranges: {}, names })).toEqual([])
  })
})
