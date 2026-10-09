/**
 * Tipos del módulo `lab-tests`, reflejando el contrato OpenAPI del backend
 * (`app/modules/lab_tests/schemas.py`).
 */

export interface LabTestBase {
  code: string
  name: string
  abbreviation?: string | null
  description?: string | null
  area_id: string
  method?: string | null
  turnaround_hours?: number | null
  loinc_code?: string | null
  cups_code?: string | null
  print_label_version_id?: string | null
  result_template_version_id?: string | null
}

/** Unidades de duración válidas para los overrides (`Literal` del backend). */
export const LAB_TEST_DURATION_UNIT_LABELS = {
  minutos: 'Minutos',
  horas: 'Horas',
  dias: 'Días'
} as const

export type LabTestDurationUnit = keyof typeof LAB_TEST_DURATION_UNIT_LABELS

export const LAB_TEST_DURATION_UNITS = Object.keys(LAB_TEST_DURATION_UNIT_LABELS) as [
  LabTestDurationUnit,
  ...LabTestDurationUnit[]
]

/**
 * Precondición asignada al examen: el valor efectivo ya resuelto (override
 * si existe, si no el del catálogo `preconditions`) y los overrides crudos
 * (`*_override`, `null` si no hay).
 */
export interface LabTestPreconditionRead {
  /** Id de la fila de asignación (historial: `useActivity`). */
  id: string
  precondition_id: string
  is_mandatory: boolean
  sort_order: number
  /** `false` = asignación quitada (solo con `include_inactive`). */
  is_active: boolean
  name: string
  description: string | null
  duration_value: number | null
  duration_unit: LabTestDurationUnit | null
  patient_instructions: string | null
  name_override: string | null
  description_override: string | null
  duration_value_override: number | null
  duration_unit_override: LabTestDurationUnit | null
  patient_instructions_override: string | null
}

/** Un elemento del body de `PUT /lab-tests/{id}/preconditions`: reemplaza el set completo. */
export interface LabTestPreconditionInput {
  precondition_id: string
  is_mandatory?: boolean
  sort_order: number
  name_override?: string | null
  description_override?: string | null
  duration_value_override?: number | null
  duration_unit_override?: LabTestDurationUnit | null
  patient_instructions_override?: string | null
}

export interface LabTestSampleTypeRead {
  /** Id de la fila de asignación (historial: `useActivity`). */
  id: string
  sample_type_id: string
  is_preferred: boolean
  required_volume_ml: number | null
  sort_order: number
  /** `false` = asignación quitada (solo con `include_inactive`). */
  is_active: boolean
}

/**
 * Un elemento del body de `PUT /lab-tests/{id}/sample-types`: reemplaza el
 * set completo. Debe existir exactamente un `is_preferred=true` (422 si no).
 */
export interface LabTestSampleTypeInput {
  sample_type_id: string
  is_preferred?: boolean
  required_volume_ml?: number | null
  sort_order: number
}

export interface LabTestConsentDocumentRead {
  /** Id de la fila de asignación (historial: `useActivity`). */
  id: string
  consent_document_version_id: string
  is_mandatory: boolean
  /** `false` = asignación quitada (solo con `include_inactive`). */
  is_active: boolean
}

/**
 * `GET /lab-tests/{id}/preconditions|sample-types|consent-documents`: por
 * defecto solo las asignaciones vigentes; con `include_inactive` también las
 * quitadas (los PUT son un diff: lo que no se envía se desactiva).
 */
export interface LabTestAssignmentListParams {
  include_inactive?: boolean
}

/**
 * Un elemento del body de `PUT /lab-tests/{id}/consent-documents`: reemplaza
 * el set completo. La versión referenciada debe estar `published` (422 si no).
 */
export interface LabTestConsentDocumentInput {
  consent_document_version_id: string
  is_mandatory?: boolean
}

export interface LabTestRead extends LabTestBase {
  id: string
  is_active: boolean
  created_at: string
  updated_at: string
  /** `[]` en el listado (resumen); resuelto en el detalle (`GET /lab-tests/{id}`). */
  preconditions: LabTestPreconditionRead[]
  /** `[]` en el listado (resumen); resuelto en el detalle (`GET /lab-tests/{id}`). */
  sample_types: LabTestSampleTypeRead[]
  /** `[]` en el listado (resumen); resuelto en el detalle (`GET /lab-tests/{id}`). */
  consent_documents: LabTestConsentDocumentRead[]
}

/**
 * `POST /lab-tests`: exige `sample_types` (el recipiente que consume el
 * examen): mínimo uno y exactamente un `is_preferred`. 422: `validation_error`
 * (`details.field="sample_types"`), conteo de preferidos
 * (`details.preferred_count`), `invalid_reference` (`details.invalid_ids`) e
 * `inactive_reference`.
 */
export interface LabTestCreate extends LabTestBase {
  is_active?: boolean
  sample_types: LabTestSampleTypeInput[]
}

/** Todos los campos opcionales: PATCH parcial. */
export type LabTestUpdate = Partial<LabTestBase & { is_active: boolean, activity_reason: string | null }>

export interface LabTestListParams {
  page?: number
  page_size?: number
  active?: boolean
  /** Búsqueda de texto (`?q=`): insensible a mayúsculas y tildes. */
  q?: string
  area_id?: string
}

// --------------------------------------------------------------------------
// Catálogos relacionados (solo lectura). El examen los enlaza por id; para
// elegirlos, este módulo consulta la API de cada catálogo con sus propios
// tipos mínimos (no usa composables ni tipos de otras layers).
// --------------------------------------------------------------------------

/** Subconjunto de `LabAreaRead`, `PrintLabelRead`, `ResultTemplateRead`, `ConsentDocumentRead`. */
export interface LabTestCatalogOption {
  id: string
  code: string
  name: string
  is_active: boolean
}

/**
 * Subconjunto de `ConsentDocumentRead`: el tipo decide si se puede enlazar a un
 * examen (el consentimiento general `tratamiento_datos` NO se enlaza).
 */
export interface LabTestConsentDocumentOption extends LabTestCatalogOption {
  document_type: string
}

/** Subconjunto de las `*VersionRead` de etiquetas, plantillas y documentos. */
export interface LabTestVersionOption {
  id: string
  version_number: number
  status: 'draft' | 'published' | 'retired'
}

/**
 * Subconjunto de las `*VersionWithOwnerRead` (`GET /print-label-versions/{id}`,
 * `/result-template-versions/{id}`, `/consent-document-versions/{id}`): la
 * versión con su entidad dueña.
 */
export interface LabTestVersionWithOwner extends LabTestVersionOption {
  owner: LabTestCatalogOption
}

/** Subconjunto de `PreconditionRead` (raíz con `items` anidados). */
export interface LabTestPreconditionOption {
  id: string
  code: string
  name: string
  category: string
  description: string | null
  duration_value: number | null
  duration_unit: string | null
  patient_instructions: string | null
  is_active: boolean
  items?: LabTestPreconditionOption[] | null
}

/** Subconjunto de `SampleTypeRead`. */
export interface LabTestSampleTypeOption {
  id: string
  code: string
  name: string
  specimen: string
  is_active: boolean
}

/** Subconjunto de `SampleRead` (con sus tipos). */
export interface LabTestSampleOption {
  id: string
  code: string
  name: string
  is_active: boolean
  types: LabTestSampleTypeOption[]
}
