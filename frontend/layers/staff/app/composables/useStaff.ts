import type { Page } from '~/types/api'
import type { StaffCreate, StaffListParams, StaffRead, StaffUpdate } from '../types/staff'

/**
 * Llamadas a la API del módulo `staff`, vía el cliente HTTP del núcleo (useLeoAppApi).
 */
export function useStaff() {
  const api = useLeoAppApi()

  function list(params: StaffListParams = {}, opts: { cacheTtl?: number, signal?: AbortSignal } = {}) {
    return api.get<Page<StaffRead>>('/staff', { params, ...opts })
  }

  function get(id: string) {
    return api.get<StaffRead>(`/staff/${id}`)
  }

  function create(payload: StaffCreate) {
    return api.post<StaffRead>('/staff', payload)
  }

  function update(id: string, payload: StaffUpdate) {
    return api.patch<StaffRead>(`/staff/${id}`, payload)
  }

  return { list, get, create, update }
}
