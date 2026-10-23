import type { Page } from '~/types/api'
import type {
  PrintLabelCreate,
  PrintLabelListParams,
  PrintLabelRead,
  PrintLabelUpdate,
  PrintLabelVersionCreate,
  PrintLabelVersionListParams,
  PrintLabelVersionRead,
  PrintLabelVersionUpdate
} from '../types/print-labels'

/**
 * Llamadas a la API del módulo `print-labels`, vía el cliente HTTP del
 * núcleo (useLeoAppApi).
 */
export function usePrintLabels() {
  const api = useLeoAppApi()

  function list(params: PrintLabelListParams = {}, opts: { cacheTtl?: number, signal?: AbortSignal } = {}) {
    return api.get<Page<PrintLabelRead>>('/print-labels', { params, ...opts })
  }

  function get(id: string) {
    return api.get<PrintLabelRead>(`/print-labels/${id}`)
  }

  function create(payload: PrintLabelCreate) {
    return api.post<PrintLabelRead>('/print-labels', payload)
  }

  function update(id: string, payload: PrintLabelUpdate) {
    return api.patch<PrintLabelRead>(`/print-labels/${id}`, payload)
  }

  function listVersions(id: string, params: PrintLabelVersionListParams = {}) {
    return api.get<Page<PrintLabelVersionRead>>(`/print-labels/${id}/versions`, { params })
  }

  function createVersion(id: string, payload: PrintLabelVersionCreate = {}) {
    return api.post<PrintLabelVersionRead>(`/print-labels/${id}/versions`, payload)
  }

  function updateVersion(id: string, versionId: string, payload: PrintLabelVersionUpdate) {
    return api.patch<PrintLabelVersionRead>(`/print-labels/${id}/versions/${versionId}`, payload)
  }

  function publishVersion(id: string, versionId: string) {
    return api.post<PrintLabelVersionRead>(`/print-labels/${id}/versions/${versionId}/publish`)
  }

  function retireVersion(id: string, versionId: string) {
    return api.post<PrintLabelVersionRead>(`/print-labels/${id}/versions/${versionId}/retire`)
  }

  return {
    list,
    get,
    create,
    update,
    listVersions,
    createVersion,
    updateVersion,
    publishVersion,
    retireVersion
  }
}
