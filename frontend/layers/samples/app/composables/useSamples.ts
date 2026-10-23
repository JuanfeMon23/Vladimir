import type { Page } from '~/types/api'
import type {
  SampleCreate,
  SampleListParams,
  SampleRead,
  SampleTypeCreate,
  SampleTypeRead,
  SampleTypeUpdate,
  SampleUpdate
} from '../types/samples'

/**
 * Llamadas a la API del módulo `samples`, vía el cliente HTTP del núcleo (useLeoAppApi).
 */
export function useSamples() {
  const api = useLeoAppApi()

  function list(params: SampleListParams = {}) {
    return api.get<Page<SampleRead>>('/samples', { params })
  }

  function get(id: string) {
    return api.get<SampleRead>(`/samples/${id}`)
  }

  function create(payload: SampleCreate) {
    return api.post<SampleRead>('/samples', payload)
  }

  function update(id: string, payload: SampleUpdate) {
    return api.patch<SampleRead>(`/samples/${id}`, payload)
  }

  function listTypes(sampleId: string) {
    return api.get<Page<SampleTypeRead>>(`/samples/${sampleId}/types`)
  }

  function createType(sampleId: string, payload: SampleTypeCreate) {
    return api.post<SampleTypeRead>(`/samples/${sampleId}/types`, payload)
  }

  function updateType(typeId: string, payload: SampleTypeUpdate) {
    return api.patch<SampleTypeRead>(`/sample-types/${typeId}`, payload)
  }

  return { list, get, create, update, listTypes, createType, updateType }
}
