import { ApiRequestError } from '~/composables/useApi'

export interface ApiFormErrors {
  /** Error general del formulario (se muestra en `UiAlert`); `null` si todo se mapeó a campos. */
  formError: string | null
  /** Errores por campo (ruta del campo → mensaje), listos para `setErrors` de vee-validate. */
  fieldErrors: Record<string, string>
}

export interface MapApiErrorOptions {
  /** Campos que existen en el formulario; solo esos reciben error por campo. */
  fields: readonly string[]
  /**
   * Traducción de claves del backend a rutas del formulario cuando difieren
   * (p. ej. `{ area_id: 'area' }`).
   */
  fieldMap?: Record<string, string>
}

const GENERIC_MESSAGE = 'Ocurrió un error inesperado. Intenta de nuevo.'

/**
 * Traduce un error de `useApi` a errores de formulario.
 *
 * - `AppError` del backend (`{ code, message, details }`, p. ej. 409 conflict
 *   o 422 validation_error): si `details` es un objeto cuyas claves son campos
 *   del formulario (p. ej. `{ code: "LAB-01" }` en un duplicado), el `message`
 *   se asigna a esos campos (o al campo que nombra `details.field`); si no,
 *   queda como error general.
 * - 422 de schema de FastAPI (`code: 'request_validation'`, `details` =
 *   `[{ loc, msg }]`): cada entrada cuyo último segmento de `loc` es un campo
 *   del formulario se asigna a ese campo.
 * - Cualquier otro error: error general.
 */
export function mapApiErrorToForm(err: unknown, options: MapApiErrorOptions): ApiFormErrors {
  if (!(err instanceof ApiRequestError)) {
    return { formError: err instanceof Error && err.message ? err.message : GENERIC_MESSAGE, fieldErrors: {} }
  }

  const known = new Set(options.fields)
  const resolve = (key: string): string | null => {
    const mapped = options.fieldMap?.[key] ?? key
    return known.has(mapped) ? mapped : null
  }

  const fieldErrors: Record<string, string> = {}
  const details = err.details

  if (err.code === 'request_validation' && Array.isArray(details)) {
    for (const entry of details) {
      if (!entry || typeof entry !== 'object') continue
      const { loc, msg } = entry as { loc?: unknown, msg?: unknown }
      if (!Array.isArray(loc) || typeof msg !== 'string') continue
      const last = [...loc].reverse().find((part): part is string => typeof part === 'string')
      const field = last ? resolve(last) : null
      if (field && !fieldErrors[field]) fieldErrors[field] = msg
    }
  } else if (details && typeof details === 'object' && !Array.isArray(details)) {
    for (const key of Object.keys(details)) {
      const field = resolve(key)
      if (field) fieldErrors[field] = err.message
    }
    // `details.field` = nombre del campo afectado (p. ej. `{ field: "sample_types" }`).
    const named = (details as { field?: unknown }).field
    const namedField = typeof named === 'string' ? resolve(named) : null
    if (namedField) fieldErrors[namedField] = err.message
  }

  const hasFieldErrors = Object.keys(fieldErrors).length > 0
  return { formError: hasFieldErrors ? null : err.message || GENERIC_MESSAGE, fieldErrors }
}
