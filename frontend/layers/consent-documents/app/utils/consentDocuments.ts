import { ApiRequestError } from '~/composables/useApi'
import { pdfFileErrorMessage } from '~/utils/pdfFile'
import type { ConsentDocumentType } from '../types/consent-documents'

/** Nombre de la descarga de una versión: `<codigo>-v<N>.pdf`. */
export function consentDocumentFilename(code: string, versionNumber: number): string {
  return `${code.replace(/[^\w.-]+/g, '-')}-v${versionNumber}.pdf`
}

/** El consentimiento general (se firma primero; a lo sumo uno activo; no se enlaza a exámenes). */
export function isGeneralConsent(document: { document_type: ConsentDocumentType }): boolean {
  return document.document_type === 'tratamiento_datos'
}

/**
 * Mensaje en español de un 422 al subir el archivo
 * (`details = { field: "file_base64", reason }`); `null` si el error no es del archivo.
 */
export function consentFileApiError(err: unknown): string | null {
  if (!(err instanceof ApiRequestError)) return null
  const details = err.details as { field?: unknown, reason?: unknown } | null | undefined
  if (!details || typeof details !== 'object' || details.field !== 'file_base64') return null
  return pdfFileErrorMessage(details.reason, err.message)
}

const MISSING_LABELS: Record<string, string> = {
  file_base64: 'Adjunta el PDF antes de publicar.',
  content: 'Falta el contenido.',
  signer: 'Falta el firmante.'
}

/** Qué falta para publicar (`details.missing_fields` del 422), en español. */
export function describeConsentPublishErrors(details: unknown): string[] {
  const missing = (details as { missing_fields?: unknown } | null | undefined)?.missing_fields
  if (!Array.isArray(missing)) return []
  return missing
    .filter((field): field is string => typeof field === 'string')
    .map(field => MISSING_LABELS[field] ?? `Falta: ${field}.`)
}

/**
 * 409 de segundo consentimiento general activo: `details = { code, id }` del
 * documento que ya lo es (el código duplicado trae solo `code`).
 */
export function isGeneralDocumentConflict(err: unknown): boolean {
  if (!(err instanceof ApiRequestError) || err.status !== 409) return false
  const details = err.details as { id?: unknown } | null | undefined
  return typeof details?.id === 'string'
}
