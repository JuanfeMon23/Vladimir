/**
 * Utilidades de archivos PDF para subir y ver adjuntos (documentos a firmar).
 * El backend recibe el archivo como base64 PURO (sin prefijo `data:`), con tope
 * de 5 MB decodificado.
 *
 * El base64 es pesado: se genera solo al enviar y se descarta; no se guarda en
 * estado reactivo.
 */

export const PDF_MAX_BYTES = 5 * 1024 * 1024
export const PDF_CONTENT_TYPE = 'application/pdf'

/** `details.reason` del 422 del backend al subir, y los motivos de la validación en cliente. */
export type PdfFileReason = 'empty' | 'too_large' | 'invalid_base64' | 'not_pdf'

export const PDF_FILE_ERROR_MESSAGES: Record<PdfFileReason, string> = {
  empty: 'El archivo está vacío.',
  too_large: 'El archivo supera los 5 MB.',
  invalid_base64: 'El archivo no se pudo leer correctamente.',
  not_pdf: 'El archivo no es un PDF válido.'
}

/** Mensaje en español de un `reason`; `fallback` si no se reconoce. */
export function pdfFileErrorMessage(reason: unknown, fallback = 'No se pudo procesar el archivo.'): string {
  return typeof reason === 'string' && reason in PDF_FILE_ERROR_MESSAGES
    ? PDF_FILE_ERROR_MESSAGES[reason as PdfFileReason]
    : fallback
}

/**
 * Validación en cliente ANTES de enviar: extensión `.pdf` y tipo PDF (o vacío,
 * que algunos navegadores no informan), no vacío y ≤ 5 MB. `null` = válido.
 */
export function validatePdfFile(file: { name: string, type: string, size: number }): PdfFileReason | null {
  const isPdf = file.name.toLowerCase().endsWith('.pdf') && (file.type === '' || file.type === PDF_CONTENT_TYPE)
  if (!isPdf) return 'not_pdf'
  if (file.size === 0) return 'empty'
  if (file.size > PDF_MAX_BYTES) return 'too_large'
  return null
}

const CHUNK = 0x8000

/** Base64 puro (sin `data:`) del contenido de un archivo/Blob. */
export async function fileToBase64(blob: Blob): Promise<string> {
  const bytes = new Uint8Array(await blob.arrayBuffer())
  let binary = ''
  for (let i = 0; i < bytes.length; i += CHUNK) {
    binary += String.fromCharCode(...bytes.subarray(i, i + CHUNK))
  }
  return btoa(binary)
}

/** Blob con los bytes de un base64 puro. */
export function base64ToBlob(base64: string, contentType = PDF_CONTENT_TYPE): Blob {
  const binary = atob(base64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
  return new Blob([bytes], { type: contentType })
}

/** Tamaño legible: `512 B`, `1,5 KB`, `2,3 MB`. */
export function formatFileSize(bytes: number): string {
  const format = (value: number, unit: string) => `${value.toFixed(1).replace(/\.0$/, '').replace('.', ',')} ${unit}`
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return format(bytes / 1024, 'KB')
  return format(bytes / (1024 * 1024), 'MB')
}

/** Huella corta para mostrar (`aaaaaaaabbbb…`); la completa se ofrece para copiar. */
export function shortSha(sha: string, length = 12): string {
  return sha.length > length ? `${sha.slice(0, length)}…` : sha
}

/** Descarga un Blob con ese nombre (URL temporal revocada al terminar). */
export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
