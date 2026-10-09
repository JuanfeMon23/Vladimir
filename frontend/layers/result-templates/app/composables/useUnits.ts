import type { Page } from '~/types/api'
import type { UnitCreate, UnitListParams, UnitRead, UnitUpdate } from '../types/result-templates'

/**
 * Llamadas a la API del catálogo de unidades de medida (`units`, códigos
 * UCUM), vía el cliente HTTP del núcleo (useApi).
 */
export function useUnits() {
  const api = useApi()

  /** `opts.cacheTtl`: pide con caché (catálogo para selects). */
  function list(params: UnitListParams = {}, opts: { cacheTtl?: number } = {}) {
    return api.get<Page<UnitRead>>('/units', { params, ...opts })
  }

  function get(id: string) {
    return api.get<UnitRead>(`/units/${id}`)
  }

  function create(payload: UnitCreate) {
    return api.post<UnitRead>('/units', payload)
  }

  function update(id: string, payload: UnitUpdate) {
    return api.patch<UnitRead>(`/units/${id}`, payload)
  }

  return { list, get, create, update }
}
