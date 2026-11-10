/**
 * Tipos del módulo `consent-documents`, reflejando el contrato OpenAPI del
 * backend (`app/modules/consent_documents/schemas.py`).
 */

/**
 * `document_type` y `signer` son el `code` de un valor de los catálogos
 * `consent-document-types` y `consent-signers` (`/catalogs/*`); las etiquetas
 * salen de la API, no de una lista en el código.
 */
export const CONSENT_GENERAL_DOCUMENT_TYPE = 'tratamiento_datos'

/** Ayuda del tipo de documento: el general se firma primero y solo hay uno activo. */
export const CONSENT_GENERAL_HINT = 'El consentimiento general se firma antes de cualquier examen; solo puede haber uno activo.'

export interface ConsentDocumentBase {
  code: string
  name: string
  description?: string | null
  document_type: string
}

export interface ConsentDocumentRead extends ConsentDocumentBase {
  id: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ConsentDocumentCreate extends ConsentDocumentBase {
  is_active?: boolean
}

/** Todos los campos opcionales: PATCH parcial. */
export type ConsentDocumentUpdate = Partial<ConsentDocumentBase & { is_active: boolean, activity_reason: string | null }>

export type ConsentDocumentListParams = {
  page?: number
  page_size?: number
  active?: boolean
  /** Búsqueda de texto (`?q=`): insensible a mayúsculas y tildes. */
  q?: string
}

export type ConsentDocumentVersionStatus = 'draft' | 'published' | 'retired'

export interface ConsentDocumentVersionRead {
  id: string
  consent_document_id: string
  version_number: number
  status: ConsentDocumentVersionStatus
  published_at: string | null
  change_notes: string | null
  content: string
  signer: string
  /** Metadatos del PDF adjunto; el contenido NO viaja aquí (`GET /consent-document-versions/{id}/file`). */
  has_file: boolean
  file_content_type: string | null
  file_sha256: string | null
  file_size_bytes: number | null
  created_at: string
  updated_at: string
}

/** `GET /consent-document-versions/{id}/file`: el PDF en base64 puro (404 si no hay archivo). */
export interface ConsentDocumentFileRead {
  content_type: string
  sha256: string
  size_bytes: number
  base64: string
}

/**
 * Body de `POST /consent-documents/{id}/versions`. Si ya existe una versión
 * previa, el nuevo draft la clona y estos campos son overrides opcionales;
 * si es la primera versión, el backend exige `content` y `signer` (422 si
 * faltan).
 */
export interface ConsentDocumentVersionCreate {
  content?: string
  signer?: string
  change_notes?: string | null
  /**
   * PDF en base64 PURO (sin `data:`), ≤ 5 MB. En el PATCH: string = reemplaza,
   * `null` = quita, omitido = no toca. Solo en borradores.
   */
  file_base64?: string | null
}

/** Todos los campos opcionales: PATCH parcial. Solo aplica sobre un draft. */
export type ConsentDocumentVersionUpdate = ConsentDocumentVersionCreate

/**
 * Contenido inicial de la primera versión (el backend exige `content` y
 * `signer` si no hay versión que clonar; el firmante se toma del catálogo).
 */
export const CONSENT_DOCUMENT_FIRST_VERSION_CONTENT = '# Título del documento\n\nRedacta aquí el contenido del documento.'

export type ConsentDocumentVersionListParams = {
  page?: number
  page_size?: number
}
