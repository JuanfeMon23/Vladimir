import type { Page } from '~/types/api'
import type {
  AssignManagerPayload,
  LabAreaCreate,
  LabAreaListParams,
  LabAreaRead,
  LabAreaStaffOption,
  LabAreaUpdate,
  ManagerAssignmentRead
} from '../types/lab-areas'

/**
 * Llamadas a la API del módulo `lab-areas`, vía el cliente HTTP del núcleo (useApi).
 */
export function useLabAreas() {
  const api = useApi()

  function list(params: LabAreaListParams = {}) {
    return api.get<Page<LabAreaRead>>('/lab-areas', { params })
  }

  function get(id: string) {
    return api.get<LabAreaRead>(`/lab-areas/${id}`)
  }

  function create(payload: LabAreaCreate) {
    return api.post<LabAreaRead>('/lab-areas', payload)
  }

  function update(id: string, payload: LabAreaUpdate) {
    return api.patch<LabAreaRead>(`/lab-areas/${id}`, payload)
  }

  function assignManager(id: string, payload: AssignManagerPayload) {
    return api.put<ManagerAssignmentRead>(`/lab-areas/${id}/manager`, payload)
  }

  function managerHistory(id: string) {
    return api.get<ManagerAssignmentRead[]>(`/lab-areas/${id}/manager-history`)
  }

  /** Personal activo elegible como encargado (`GET /staff?active=true`). */
  function listEligibleManagers() {
    return api.get<Page<LabAreaStaffOption>>('/staff', { params: { active: true, page_size: 100 }, cacheTtl: CATALOG_CACHE_TTL })
  }

  return { list, get, create, update, assignManager, managerHistory, listEligibleManagers }
}
