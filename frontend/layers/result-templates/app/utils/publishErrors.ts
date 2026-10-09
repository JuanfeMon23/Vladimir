import { RESULT_TYPE_LABELS } from '../types/result-templates'
import { describeFormulaProblem } from './formulaProblems'
import type {
  ResultTemplatePublishInactiveEntry,
  ResultTemplatePublishInvalidFormulaEntry,
  ResultTemplatePublishMissingEntry,
  ResultType
} from '../types/result-templates'

/** Qué falta, en español, por cada `missing_fields` del backend. */
const MISSING_LABELS: Record<string, string> = {
  unit_id: 'unidad',
  decimals: 'decimales',
  option_set_id: 'conjunto de opciones',
  formula: 'fórmula',
  reference_ranges: 'al menos un rango de referencia activo'
}

/** Sujeto (con artículo) y concordancia de cada `field` de `details.inactive`. */
const INACTIVE_SUBJECTS: Record<string, { subject: string, feminine: boolean }> = {
  analyte_id: { subject: 'el analito', feminine: false },
  unit_id: { subject: 'la unidad', feminine: true },
  option_set_id: { subject: 'el conjunto de opciones', feminine: false },
  section_id: { subject: 'la sección', feminine: true },
  expected_option_id: { subject: 'la opción esperada de un rango', feminine: true }
}

export interface ResultTemplatePublishErrorNames {
  /** Nombre legible de un analito de la plantilla. */
  templateAnalyte: (templateAnalyteId: string) => string
  /** Nombre legible de un elemento referenciado (`field` de `details.inactive`). */
  reference: (field: string, id: string) => string
}

function joinSpanish(items: string[]) {
  if (items.length <= 1) return items.join('')
  return `${items.slice(0, -1).join(', ')} y ${items[items.length - 1]}`
}

function asArray<T>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : []
}

/**
 * Líneas legibles del 422 al publicar una versión de plantilla
 * (`details.missing`, `details.inactive` y `details.invalid_formula`), una por
 * analito incompleto, una por referencia desactivada y una por fórmula inválida.
 */
export function describeResultTemplatePublishErrors(
  details: unknown,
  names: ResultTemplatePublishErrorNames
): string[] {
  if (!details || typeof details !== 'object') return []
  const { missing, inactive, invalid_formula: invalidFormula } = details as { missing?: unknown, inactive?: unknown, invalid_formula?: unknown }
  const lines: string[] = []

  for (const entry of asArray<ResultTemplatePublishMissingEntry>(missing)) {
    const type = RESULT_TYPE_LABELS[entry.result_type as ResultType] ?? entry.result_type
    const parts: string[] = []
    const fields = (entry.missing_fields ?? []).map(field => MISSING_LABELS[field] ?? field)
    if (fields.length) parts.push(`falta ${joinSpanish(fields)}`)
    const incompatible = entry.incompatible_reference_range_ids?.length ?? 0
    if (incompatible === 1) parts.push('1 rango de referencia usa campos que su tipo de resultado no admite')
    else if (incompatible > 1) parts.push(`${incompatible} rangos de referencia usan campos que su tipo de resultado no admite`)
    if (parts.length) lines.push(`${names.templateAnalyte(entry.template_analyte_id)} (${type}): ${parts.join('; ')}.`)
  }

  for (const entry of asArray<ResultTemplatePublishInactiveEntry>(inactive)) {
    const known = INACTIVE_SUBJECTS[entry.field]
    const subject = known?.subject ?? entry.field
    const adjective = known?.feminine ? 'inactiva' : 'inactivo'
    lines.push(`${names.templateAnalyte(entry.template_analyte_id)}: ${subject} «${names.reference(entry.field, entry.id)}» está ${adjective}.`)
  }

  for (const entry of asArray<ResultTemplatePublishInvalidFormulaEntry>(invalidFormula)) {
    lines.push(`${names.templateAnalyte(entry.template_analyte_id)}: fórmula inválida. ${describeFormulaProblem(entry)}`)
  }

  return lines
}
