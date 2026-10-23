import type { Page } from '~/types/api'
import type {
  ResultOptionCreate,
  ResultOptionListParams,
  ResultOptionRead,
  ResultOptionSetCreate,
  ResultOptionSetListParams,
  ResultOptionSetRead,
  ResultOptionSetUpdate,
  ResultOptionUpdate
} from '../types/result-templates'

/**
 * Llamadas a la API de `result-option-sets` y su sub-recurso `options`, más
 * `result-options/{id}` (PATCH directo), vía el cliente HTTP del núcleo
 * (useLeoAppApi).
 */
export function useResultOptionSets() {
  const api = useLeoAppApi()

  /** `opts.cacheTtl`: pide con caché (catálogo para selects). */
  function list(params: ResultOptionSetListParams = {}, opts: { cacheTtl?: number, signal?: AbortSignal } = {}) {
    return api.get<Page<ResultOptionSetRead>>('/result-option-sets', { params, ...opts })
  }

  function get(id: string) {
    return api.get<ResultOptionSetRead>(`/result-option-sets/${id}`)
  }

  function create(payload: ResultOptionSetCreate) {
    return api.post<ResultOptionSetRead>('/result-option-sets', payload)
  }

  function update(id: string, payload: ResultOptionSetUpdate) {
    return api.patch<ResultOptionSetRead>(`/result-option-sets/${id}`, payload)
  }

  function listOptions(optionSetId: string, params: ResultOptionListParams = {}, opts: { cacheTtl?: number } = {}) {
    return api.get<Page<ResultOptionRead>>(`/result-option-sets/${optionSetId}/options`, { params, ...opts })
  }

  function createOption(optionSetId: string, payload: ResultOptionCreate) {
    return api.post<ResultOptionRead>(`/result-option-sets/${optionSetId}/options`, payload)
  }

  function updateOption(optionId: string, payload: ResultOptionUpdate) {
    return api.patch<ResultOptionRead>(`/result-options/${optionId}`, payload)
  }

  return { list, get, create, update, listOptions, createOption, updateOption }
}
