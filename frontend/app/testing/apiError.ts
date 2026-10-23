import { LeoApiError } from '#leo-client/lib/errors'

/**
 * `LeoApiError` para tests a partir del `{code, message, details}` del backend
 * (solo tests; Nuxt no auto-importa `app/testing/`). Sin `status` (error de red
 * o dato irrelevante) queda en 0.
 */
export function apiError(error: { code: string, message: string, details?: unknown }, status = 0): LeoApiError {
  return new LeoApiError(status, error.code, error.message, error.details ?? null)
}
