import type { Page } from '~/types/api'
import type {
  AnalyteCreate,
  AnalyteListParams,
  AnalyteRead,
  AnalyteUpdate
} from '../types/result-templates'

/**
 * Llamadas a la API del catálogo `analytes`, vía el cliente HTTP del núcleo
 * (useLeoAppApi).
 */
export function useAnalytes() {
  const api = useLeoAppApi()

  /** `opts.cacheTtl`: pide con caché (catálogo para selects). */
  function list(params: AnalyteListParams = {}, opts: { cacheTtl?: number, signal?: AbortSignal } = {}) {
    return api.get<Page<AnalyteRead>>('/analytes', { params, ...opts })
  }

  function get(id: string) {
    return api.get<AnalyteRead>(`/analytes/${id}`)
  }

  function create(payload: AnalyteCreate) {
    return api.post<AnalyteRead>('/analytes', payload)
  }

  function update(id: string, payload: AnalyteUpdate) {
    return api.patch<AnalyteRead>(`/analytes/${id}`, payload)
  }

  return { list, get, create, update }
}
