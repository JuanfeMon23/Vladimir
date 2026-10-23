import type { Page } from '~/types/api'
import type {
  LabTestAssignmentListParams,
  LabTestCatalogOption,
  LabTestConsentDocumentInput,
  LabTestConsentDocumentOption,
  LabTestConsentDocumentRead,
  LabTestCreate,
  LabTestListParams,
  LabTestPreconditionInput,
  LabTestPreconditionOption,
  LabTestPreconditionRead,
  LabTestRead,
  LabTestSampleOption,
  LabTestSampleTypeInput,
  LabTestSampleTypeRead,
  LabTestUpdate,
  LabTestVersionOption,
  LabTestVersionWithOwner
} from '../types/lab-tests'

/**
 * Página máxima para cargar un catálogo completo (activos e inactivos): los
 * selectores ofrecen solo los activos, pero los inactivos ya asignados se
 * siguen nombrando y mostrando como "(inactivo)".
 */
const CATALOG_PAGE = { page_size: 200 }

/** Los catálogos se piden con caché (5 min; las mutaciones del recurso la invalidan). */
const CATALOG_CACHE = { cacheTtl: CATALOG_CACHE_TTL }

/** Solo versiones publicadas (las únicas que se pueden asignar a un examen). */
const PUBLISHED_VERSIONS = { page_size: 200, status: 'published' }

/**
 * Llamadas a la API del módulo `lab-tests`, vía el cliente HTTP del núcleo
 * (useLeoAppApi). Módulo central: enlaza área, versión de etiqueta, versión de
 * plantilla, precondiciones, tipos de muestra y documentos a firmar por id.
 * Para elegirlos consulta directamente la API de cada catálogo (lecturas
 * `list*Options`, con tipos propios de este módulo): una layer no usa
 * composables de otra.
 */
export function useLabTests() {
  const api = useLeoAppApi()

  function list(params: LabTestListParams = {}) {
    return api.get<Page<LabTestRead>>('/lab-tests', { params })
  }

  /** Detalle completo: precondiciones, tipos de muestra y documentos resueltos. */
  function get(id: string) {
    return api.get<LabTestRead>(`/lab-tests/${id}`)
  }

  function create(payload: LabTestCreate) {
    return api.post<LabTestRead>('/lab-tests', payload)
  }

  function update(id: string, payload: LabTestUpdate) {
    return api.patch<LabTestRead>(`/lab-tests/${id}`, payload)
  }

  function getPreconditions(id: string, params: LabTestAssignmentListParams = {}) {
    return api.get<LabTestPreconditionRead[]>(`/lab-tests/${id}/preconditions`, { params })
  }

  /** Envía el set completo de precondiciones (diff: lo que falta se desactiva; lo nuevo debe estar activo). */
  function putPreconditions(id: string, items: LabTestPreconditionInput[]) {
    return api.put<LabTestPreconditionRead[]>(`/lab-tests/${id}/preconditions`, items)
  }

  function getSampleTypes(id: string, params: LabTestAssignmentListParams = {}) {
    return api.get<LabTestSampleTypeRead[]>(`/lab-tests/${id}/sample-types`, { params })
  }

  /** Reemplaza el set completo de tipos de muestra. 422 si no hay exactamente un `is_preferred=true`. */
  function putSampleTypes(id: string, items: LabTestSampleTypeInput[]) {
    return api.put<LabTestSampleTypeRead[]>(`/lab-tests/${id}/sample-types`, items)
  }

  function getConsentDocuments(id: string, params: LabTestAssignmentListParams = {}) {
    return api.get<LabTestConsentDocumentRead[]>(`/lab-tests/${id}/consent-documents`, { params })
  }

  /** Reemplaza el set completo de documentos a firmar. 422 si alguna versión no está `published`. */
  function putConsentDocuments(id: string, items: LabTestConsentDocumentInput[]) {
    return api.put<LabTestConsentDocumentRead[]>(`/lab-tests/${id}/consent-documents`, items)
  }

  // --- Catálogos relacionados (solo lectura) ---

  /**
   * Todas las áreas, activas e inactivas (`GET /lab-areas`): el filtro del
   * listado y el nombre de la columna necesitan también las inactivas; el
   * formulario ofrece solo las activas (más la actual del examen).
   */
  async function listAreaOptions() {
    return (await api.get<Page<LabTestCatalogOption>>('/lab-areas', { params: CATALOG_PAGE, ...CATALOG_CACHE })).items
  }

  /** Etiquetas de impresión, activas e inactivas (`GET /print-labels`). */
  async function listPrintLabelOptions() {
    return (await api.get<Page<LabTestCatalogOption>>('/print-labels', { params: CATALOG_PAGE, ...CATALOG_CACHE })).items
  }

  /** Versiones publicadas de una etiqueta (`GET /print-labels/{id}/versions?status=published`). */
  async function listPublishedPrintLabelVersions(printLabelId: string) {
    return (await api.get<Page<LabTestVersionOption>>(`/print-labels/${printLabelId}/versions`, { params: PUBLISHED_VERSIONS, ...CATALOG_CACHE })).items
  }

  /** Una versión de etiqueta con su etiqueta dueña (`GET /print-label-versions/{id}`; 404 si no existe). */
  function getPrintLabelVersion(versionId: string) {
    return api.get<LabTestVersionWithOwner>(`/print-label-versions/${versionId}`)
  }

  /** Plantillas de resultados, activas e inactivas (`GET /result-templates`). */
  async function listResultTemplateOptions() {
    return (await api.get<Page<LabTestCatalogOption>>('/result-templates', { params: CATALOG_PAGE, ...CATALOG_CACHE })).items
  }

  /** Versiones publicadas de una plantilla (`GET /result-templates/{id}/versions?status=published`). */
  async function listPublishedResultTemplateVersions(resultTemplateId: string) {
    return (await api.get<Page<LabTestVersionOption>>(`/result-templates/${resultTemplateId}/versions`, { params: PUBLISHED_VERSIONS, ...CATALOG_CACHE })).items
  }

  /** Una versión de plantilla con su plantilla dueña (`GET /result-template-versions/{id}`; 404 si no existe). */
  function getResultTemplateVersion(versionId: string) {
    return api.get<LabTestVersionWithOwner>(`/result-template-versions/${versionId}`)
  }

  /** Precondiciones (activas e inactivas) con sus ítems (`GET /preconditions`). */
  async function listPreconditionOptions() {
    return (await api.get<Page<LabTestPreconditionOption>>('/preconditions', { params: CATALOG_PAGE, ...CATALOG_CACHE })).items
  }

  /** Muestras (activas e inactivas) con sus tipos (`GET /samples`). */
  async function listSampleOptions() {
    return (await api.get<Page<LabTestSampleOption>>('/samples', { params: CATALOG_PAGE, ...CATALOG_CACHE })).items
  }

  /** Documentos a firmar, activos e inactivos (`GET /consent-documents`). */
  async function listConsentDocumentOptions() {
    return (await api.get<Page<LabTestConsentDocumentOption>>('/consent-documents', { params: CATALOG_PAGE, ...CATALOG_CACHE })).items
  }

  /** Versiones publicadas de un documento a firmar (`GET /consent-documents/{id}/versions?status=published`). */
  async function listPublishedConsentDocumentVersions(consentDocumentId: string) {
    return (await api.get<Page<LabTestVersionOption>>(`/consent-documents/${consentDocumentId}/versions`, { params: PUBLISHED_VERSIONS, ...CATALOG_CACHE })).items
  }

  /** Una versión de documento con su documento dueño (`GET /consent-document-versions/{id}`; 404 si no existe). */
  function getConsentDocumentVersion(versionId: string) {
    return api.get<LabTestVersionWithOwner>(`/consent-document-versions/${versionId}`)
  }

  return {
    list,
    get,
    create,
    update,
    getPreconditions,
    putPreconditions,
    getSampleTypes,
    putSampleTypes,
    getConsentDocuments,
    putConsentDocuments,
    listAreaOptions,
    listPrintLabelOptions,
    listPublishedPrintLabelVersions,
    getPrintLabelVersion,
    listResultTemplateOptions,
    listPublishedResultTemplateVersions,
    getResultTemplateVersion,
    listPreconditionOptions,
    listSampleOptions,
    listConsentDocumentOptions,
    listPublishedConsentDocumentVersions,
    getConsentDocumentVersion
  }
}
