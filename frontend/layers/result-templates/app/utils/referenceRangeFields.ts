import type { ResultTypeBehavior } from '~/types/catalogs'
import { REFERENCE_RANGE_TYPED_FIELDS } from '../types/result-templates'
import type { ReferenceRangeTypedField } from '../types/result-templates'

const NUMERIC_FIELDS: readonly ReferenceRangeTypedField[] = ['low', 'high', 'critical_low', 'critical_high']

type RangeBehavior = Pick<ResultTypeBehavior, 'uses_numeric_range' | 'uses_option_set' | 'uses_boolean_range'>

/**
 * Campos tipados de un rango de referencia que admite un tipo de resultado,
 * según las banderas de su fila del catálogo `result-types` (el backend rechaza
 * con 422 `validation_error` / `details.not_allowed` un campo no admitido con
 * valor): `uses_numeric_range` → límites normales y críticos;
 * `uses_option_set` → `expected_option_id`; `uses_boolean_range` →
 * `expected_boolean`. `display_text`, `interpretation`, sexo, edad y condición
 * valen para todos. Sin el tipo (catálogo no cargado) no hay campos tipados.
 */
export function resultTemplateRangeFields(behavior: RangeBehavior | undefined): ReferenceRangeTypedField[] {
  if (!behavior) return []
  return [
    ...(behavior.uses_numeric_range ? NUMERIC_FIELDS : []),
    ...(behavior.uses_option_set ? ['expected_option_id' as const] : []),
    ...(behavior.uses_boolean_range ? ['expected_boolean' as const] : [])
  ]
}

/**
 * Payload de un rango sin los campos tipados que el tipo de resultado no
 * admite (no se envían: ni con valor ni en `null`).
 */
export function pickResultTemplateRangeValues<T extends Record<string, unknown>>(
  values: T,
  behavior: RangeBehavior | undefined
): Partial<T> {
  const allowed = new Set<string>(resultTemplateRangeFields(behavior))
  const typed = new Set<string>(REFERENCE_RANGE_TYPED_FIELDS)
  return Object.fromEntries(
    Object.entries(values).filter(([key]) => !typed.has(key) || allowed.has(key))
  ) as Partial<T>
}
