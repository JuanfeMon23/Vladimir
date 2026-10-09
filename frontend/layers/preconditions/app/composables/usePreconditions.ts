import type { Page } from '~/types/api'
import type {
  PreconditionCreate,
  PreconditionListParams,
  PreconditionRead,
  PreconditionUpdate
} from '../types/preconditions'

/**
 * Llamadas a la API del módulo `preconditions`, vía el cliente HTTP del núcleo (useApi).
 */
export function usePreconditions() {
  const api = useApi()

  function list(params: PreconditionListParams = {}) {
    return api.get<Page<PreconditionRead>>('/preconditions', { params })
  }

  function get(id: string) {
    return api.get<PreconditionRead>(`/preconditions/${id}`)
  }

  function create(payload: PreconditionCreate) {
    return api.post<PreconditionRead>('/preconditions', payload)
  }

  /** Crea un ítem (`kind: 'condition'`) bajo la precondición raíz `parentId`. */
  function createItem(parentId: string, payload: PreconditionCreate) {
    return api.post<PreconditionRead>(`/preconditions/${parentId}/items`, payload)
  }

  function update(id: string, payload: PreconditionUpdate) {
    return api.patch<PreconditionRead>(`/preconditions/${id}`, payload)
  }

  return { list, get, create, createItem, update }
}
