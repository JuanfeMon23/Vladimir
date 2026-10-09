import { REFERENCE_RANGE_TYPED_FIELDS } from '../types/result-templates'
import type { ReferenceRangeTypedField, ResultType } from '../types/result-templates'

const NUMERIC_FIELDS: readonly ReferenceRangeTypedField[] = ['low', 'high', 'critical_low', 'critical_high']

/**
 * Campos tipados de un rango de referencia que admite cada `result_type`
 * (espejo de `_ALLOWED_RANGE_FIELDS` del backend; un campo no admitido con
 * valor da 422 `validation_error` con `details.not_allowed`). `display_text`,
 * `interpretation`, sexo, edad y condición valen para todos.
 */
const ALLOWED: Record<ResultType, readonly ReferenceRangeTypedField[]> = {
  numeric: NUMERIC_FIELDS,
  calculated: NUMERIC_FIELDS,
  qualitative: ['expected_option_id'],
  semi_quantitative: ['expected_option_id'],
  boolean: ['expected_boolean'],
  text: [],
  titer: ['expected_option_id']
}

export function resultTemplateRangeFields(resultType: ResultType): ReferenceRangeTypedField[] {
  return [...ALLOWED[resultType]]
}

/**
 * Payload de un rango sin los campos tipados que el `result_type` no admite
 * (no se envían: ni con valor ni en `null`).
 */
export function pickResultTemplateRangeValues<T extends Record<string, unknown>>(
  values: T,
  resultType: ResultType
): Partial<T> {
  const allowed = new Set<string>(ALLOWED[resultType])
  const typed = new Set<string>(REFERENCE_RANGE_TYPED_FIELDS)
  return Object.fromEntries(
    Object.entries(values).filter(([key]) => !typed.has(key) || allowed.has(key))
  ) as Partial<T>
}
