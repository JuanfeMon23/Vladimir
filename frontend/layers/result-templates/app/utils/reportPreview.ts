import { REFERENCE_RANGE_AGE_UNIT_LABELS, REFERENCE_RANGE_SEX_LABELS, RESULT_TYPE_LABELS } from '../types/result-templates'
import type {
  ReferenceRangeRead,
  ResultTemplateAnalyteRead,
  ResultTemplateSectionRead
} from '../types/result-templates'

/** Contexto para formatear los rangos de un analito. */
export interface ReferenceRangeFormatContext {
  /** Símbolo de la unidad del analito (`null` si no tiene). */
  unit: string | null
  /** Decimales del analito (`null` = tal cual). */
  decimals: number | null
  /** Etiqueta de una opción de resultado (para `expected_option_id`). */
  option: (optionId: string) => string
}

function withUnit(text: string, unit: string | null) {
  return unit ? `${text} ${unit}` : text
}

/**
 * Un rango de referencia como se leería en el reporte: `display_text` si
 * existe; si no, "low – high unidad" (o ≥ / ≤ con un solo límite), opción o
 * booleano esperado y valores críticos. Antepone sexo, edad y condición
 * (si los hay) y agrega la interpretación entre paréntesis.
 */
export function formatReferenceRange(range: ReferenceRangeRead, ctx: ReferenceRangeFormatContext): string {
  const num = (value: number) => (ctx.decimals === null ? String(value) : value.toFixed(ctx.decimals))

  let value: string
  if (range.display_text) {
    value = range.display_text
  } else {
    const parts: string[] = []
    if (range.low !== null && range.high !== null) parts.push(withUnit(`${num(range.low)} – ${num(range.high)}`, ctx.unit))
    else if (range.low !== null) parts.push(withUnit(`≥ ${num(range.low)}`, ctx.unit))
    else if (range.high !== null) parts.push(withUnit(`≤ ${num(range.high)}`, ctx.unit))
    if (range.expected_option_id) parts.push(`Esperado: ${ctx.option(range.expected_option_id)}`)
    if (range.expected_boolean !== null) parts.push(`Esperado: ${range.expected_boolean ? 'Sí' : 'No'}`)
    const critical: string[] = []
    if (range.critical_low !== null) critical.push(withUnit(`< ${num(range.critical_low)}`, ctx.unit))
    if (range.critical_high !== null) critical.push(withUnit(`> ${num(range.critical_high)}`, ctx.unit))
    if (critical.length) parts.push(`Crítico: ${critical.join(', ')}`)
    value = parts.length ? parts.join(' · ') : 'Sin valores definidos'
  }

  const who: string[] = []
  if (range.sex !== 'any') who.push(REFERENCE_RANGE_SEX_LABELS[range.sex] ?? range.sex)
  if (range.age_min !== null || range.age_max !== null) {
    const unit = range.age_unit ? ` ${(REFERENCE_RANGE_AGE_UNIT_LABELS[range.age_unit] ?? range.age_unit).toLowerCase()}` : ''
    if (range.age_min !== null && range.age_max !== null) who.push(`${range.age_min}–${range.age_max}${unit}`)
    else if (range.age_min !== null) who.push(`≥ ${range.age_min}${unit}`)
    else who.push(`≤ ${range.age_max}${unit}`)
  }
  if (range.condition) who.push(range.condition)

  const prefix = who.length ? `${who.join(' · ')}: ` : ''
  const suffix = range.interpretation ? ` (${range.interpretation})` : ''
  return `${prefix}${value}${suffix}`
}

export interface ReportPreviewRow {
  id: string
  name: string
  resultType: string
  unit: string | null
  decimals: number | null
  required: boolean
  reportable: boolean
  /** Rangos activos, ya formateados. */
  ranges: string[]
}

export interface ReportPreviewGroup {
  sectionId: string | null
  name: string
  rows: ReportPreviewRow[]
}

export interface ReportPreviewInput {
  sections: readonly ResultTemplateSectionRead[]
  analytes: readonly ResultTemplateAnalyteRead[]
  /** Rangos por id de analito de plantilla. */
  ranges: Record<string, readonly ReferenceRangeRead[]>
  names: {
    analyte: (analyteId: string) => string
    unit: (unitId: string | null) => string | null
    option: (optionId: string) => string
  }
}

/**
 * Vista previa del reporte de una versión: secciones activas en su orden, con
 * sus analitos activos en el suyo; los analitos sin sección (o de una sección
 * inactiva) van al final en "Sin sección". Los inactivos quedan fuera.
 */
export function buildReportPreview(input: ReportPreviewInput): ReportPreviewGroup[] {
  const bySort = <T extends { sort_order: number }>(a: T, b: T) => a.sort_order - b.sort_order
  const sections = input.sections.filter(section => section.is_active).sort(bySort)
  const activeSectionIds = new Set(sections.map(section => section.id))
  const analytes = input.analytes.filter(item => item.is_active).sort(bySort)

  const toRow = (item: ResultTemplateAnalyteRead): ReportPreviewRow => {
    const unit = input.names.unit(item.unit_id)
    const ctx: ReferenceRangeFormatContext = { unit, decimals: item.decimals, option: input.names.option }
    return {
      id: item.id,
      name: input.names.analyte(item.analyte_id),
      resultType: RESULT_TYPE_LABELS[item.result_type] ?? item.result_type,
      unit,
      decimals: item.decimals,
      required: item.is_required,
      reportable: item.is_reportable,
      ranges: (input.ranges[item.id] ?? []).filter(range => range.is_active).map(range => formatReferenceRange(range, ctx))
    }
  }

  const groups: ReportPreviewGroup[] = sections.map(section => ({
    sectionId: section.id,
    name: section.name,
    rows: analytes.filter(item => item.section_id === section.id).map(toRow)
  }))
  groups.push({
    sectionId: null,
    name: 'Sin sección',
    rows: analytes.filter(item => !item.section_id || !activeSectionIds.has(item.section_id)).map(toRow)
  })
  return groups.filter(group => group.rows.length > 0)
}
