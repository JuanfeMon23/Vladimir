import type { Page } from '~/types/api'
import type {
  ConsentDocumentCreate,
  ConsentDocumentFileRead,
  ConsentDocumentListParams,
  ConsentDocumentRead,
  ConsentDocumentUpdate,
  ConsentDocumentVersionCreate,
  ConsentDocumentVersionListParams,
  ConsentDocumentVersionRead,
  ConsentDocumentVersionUpdate
} from '../types/consent-documents'

/**
 * Llamadas a la API del módulo `consent-documents`, vía el cliente HTTP del
 * núcleo (useLeoAppApi).
 */
export function useConsentDocuments() {
  const api = useLeoAppApi()

  function list(params: ConsentDocumentListParams = {}, opts: { cacheTtl?: number, signal?: AbortSignal } = {}) {
    return api.get<Page<ConsentDocumentRead>>('/consent-documents', { params, ...opts })
  }

  function get(id: string) {
    return api.get<ConsentDocumentRead>(`/consent-documents/${id}`)
  }

  function create(payload: ConsentDocumentCreate) {
    return api.post<ConsentDocumentRead>('/consent-documents', payload)
  }

  function update(id: string, payload: ConsentDocumentUpdate) {
    return api.patch<ConsentDocumentRead>(`/consent-documents/${id}`, payload)
  }

  function listVersions(id: string, params: ConsentDocumentVersionListParams = {}) {
    return api.get<Page<ConsentDocumentVersionRead>>(`/consent-documents/${id}/versions`, { params })
  }

  function createVersion(id: string, payload: ConsentDocumentVersionCreate = {}) {
    return api.post<ConsentDocumentVersionRead>(`/consent-documents/${id}/versions`, payload)
  }

  function updateVersion(id: string, versionId: string, payload: ConsentDocumentVersionUpdate) {
    return api.patch<ConsentDocumentVersionRead>(`/consent-documents/${id}/versions/${versionId}`, payload)
  }

  /** El PDF de una versión (base64). Carga perezosa, sin caché: solo al verlo o descargarlo. */
  function getVersionFile(versionId: string) {
    return api.get<ConsentDocumentFileRead>(`/consent-document-versions/${versionId}/file`)
  }

  function publishVersion(id: string, versionId: string) {
    return api.post<ConsentDocumentVersionRead>(`/consent-documents/${id}/versions/${versionId}/publish`)
  }

  function retireVersion(id: string, versionId: string) {
    return api.post<ConsentDocumentVersionRead>(`/consent-documents/${id}/versions/${versionId}/retire`)
  }

  return {
    list,
    get,
    create,
    update,
    listVersions,
    createVersion,
    updateVersion,
    getVersionFile,
    publishVersion,
    retireVersion
  }
}
