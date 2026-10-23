import type { Page } from '~/types/api'
import type {
  ReferenceRangeCreate,
  ReferenceRangeRead,
  ReferenceRangeUpdate,
  ResultTemplateAnalyteCreate,
  ResultTemplateAnalyteRead,
  ResultTemplateAnalyteUpdate,
  ResultTemplateContentListParams,
  ResultTemplateCreate,
  ResultTemplateListParams,
  ResultTemplateRead,
  ResultTemplateSectionCreate,
  ResultTemplateSectionRead,
  ResultTemplateSectionUpdate,
  ResultTemplateUpdate,
  ResultTemplateVersionCreate,
  ResultTemplateVersionListParams,
  ResultTemplateVersionRead,
  ResultTemplateVersionUpdate
} from '../types/result-templates'

/**
 * Llamadas a la API del módulo `result-templates`: plantillas, versiones y,
 * dentro de cada versión (solo editable en `draft`), secciones, analitos de
 * plantilla y rangos de referencia. Vía el cliente HTTP del núcleo (useLeoAppApi).
 *
 * Secciones, analitos y rangos no se eliminan (el backend responde 405): se
 * desactivan con `update*({ is_active: false, activity_reason })`. Sus
 * listados traen solo activos salvo `{ include_inactive: true }`.
 */
export function useResultTemplates() {
  const api = useLeoAppApi()

  function list(params: ResultTemplateListParams = {}) {
    return api.get<Page<ResultTemplateRead>>('/result-templates', { params })
  }

  function get(id: string) {
    return api.get<ResultTemplateRead>(`/result-templates/${id}`)
  }

  function create(payload: ResultTemplateCreate) {
    return api.post<ResultTemplateRead>('/result-templates', payload)
  }

  function update(id: string, payload: ResultTemplateUpdate) {
    return api.patch<ResultTemplateRead>(`/result-templates/${id}`, payload)
  }

  function listVersions(id: string, params: ResultTemplateVersionListParams = {}) {
    return api.get<Page<ResultTemplateVersionRead>>(`/result-templates/${id}/versions`, { params })
  }

  function createVersion(id: string, payload: ResultTemplateVersionCreate = { report_settings: {} }) {
    return api.post<ResultTemplateVersionRead>(`/result-templates/${id}/versions`, payload)
  }

  function updateVersion(id: string, versionId: string, payload: ResultTemplateVersionUpdate) {
    return api.patch<ResultTemplateVersionRead>(`/result-templates/${id}/versions/${versionId}`, payload)
  }

  function publishVersion(id: string, versionId: string) {
    return api.post<ResultTemplateVersionRead>(`/result-templates/${id}/versions/${versionId}/publish`)
  }

  function retireVersion(id: string, versionId: string) {
    return api.post<ResultTemplateVersionRead>(`/result-templates/${id}/versions/${versionId}/retire`)
  }

  function listSections(id: string, versionId: string, params: ResultTemplateContentListParams = {}) {
    return api.get<ResultTemplateSectionRead[]>(`/result-templates/${id}/versions/${versionId}/sections`, { params })
  }

  function createSection(id: string, versionId: string, payload: ResultTemplateSectionCreate) {
    return api.post<ResultTemplateSectionRead>(`/result-templates/${id}/versions/${versionId}/sections`, payload)
  }

  function updateSection(id: string, versionId: string, sectionId: string, payload: ResultTemplateSectionUpdate) {
    return api.patch<ResultTemplateSectionRead>(
      `/result-templates/${id}/versions/${versionId}/sections/${sectionId}`,
      payload
    )
  }

  function listTemplateAnalytes(id: string, versionId: string, params: ResultTemplateContentListParams = {}) {
    return api.get<ResultTemplateAnalyteRead[]>(`/result-templates/${id}/versions/${versionId}/analytes`, { params })
  }

  function createTemplateAnalyte(id: string, versionId: string, payload: ResultTemplateAnalyteCreate) {
    return api.post<ResultTemplateAnalyteRead>(`/result-templates/${id}/versions/${versionId}/analytes`, payload)
  }

  function updateTemplateAnalyte(
    id: string,
    versionId: string,
    templateAnalyteId: string,
    payload: ResultTemplateAnalyteUpdate
  ) {
    return api.patch<ResultTemplateAnalyteRead>(
      `/result-templates/${id}/versions/${versionId}/analytes/${templateAnalyteId}`,
      payload
    )
  }

  function listReferenceRanges(
    id: string,
    versionId: string,
    templateAnalyteId: string,
    params: ResultTemplateContentListParams = {}
  ) {
    return api.get<ReferenceRangeRead[]>(
      `/result-templates/${id}/versions/${versionId}/analytes/${templateAnalyteId}/reference-ranges`,
      { params }
    )
  }

  function createReferenceRange(
    id: string,
    versionId: string,
    templateAnalyteId: string,
    payload: ReferenceRangeCreate
  ) {
    return api.post<ReferenceRangeRead>(
      `/result-templates/${id}/versions/${versionId}/analytes/${templateAnalyteId}/reference-ranges`,
      payload
    )
  }

  function updateReferenceRange(
    id: string,
    versionId: string,
    templateAnalyteId: string,
    referenceRangeId: string,
    payload: ReferenceRangeUpdate
  ) {
    return api.patch<ReferenceRangeRead>(
      `/result-templates/${id}/versions/${versionId}/analytes/${templateAnalyteId}/reference-ranges/${referenceRangeId}`,
      payload
    )
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
    retireVersion,
    listSections,
    createSection,
    updateSection,
    listTemplateAnalytes,
    createTemplateAnalyte,
    updateTemplateAnalyte,
    listReferenceRanges,
    createReferenceRange,
    updateReferenceRange
  }
}
