/**
 * Tipos del módulo `result-templates`, reflejando el contrato OpenAPI del
 * backend (`app/modules/result_templates/schemas.py`).
 */

// --------------------------------------------------------------------------
// Units (catálogo UCUM)
// --------------------------------------------------------------------------

export interface UnitBase {
  /** Código UCUM, p. ej. `mg/dL`, `10*3/uL`. */
  code: string
  /** Símbolo para mostrar en reportes. */
  symbol: string
  name: string
}

export interface UnitRead extends UnitBase {
  id: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface UnitCreate extends UnitBase {
  is_active?: boolean
}

export type UnitUpdate = Partial<UnitBase & { is_active: boolean, activity_reason: string | null }>

export type UnitListParams = {
  page?: number
  page_size?: number
  active?: boolean
  /** Búsqueda de texto (`?q=`): insensible a mayúsculas y tildes. */
  q?: string
}

/** Resumen de unidad embebido en analitos (`default_unit_detail`, `unit_detail`). */
export interface UnitSummary {
  id: string
  code: string
  symbol: string
  name: string
}

// --------------------------------------------------------------------------
// Analytes
// --------------------------------------------------------------------------

export interface AnalyteBase {
  code: string
  name: string
  loinc_code?: string | null
  default_unit_id?: string | null
  description?: string | null
}

export interface AnalyteRead extends AnalyteBase {
  id: string
  default_unit_id: string | null
  /** Símbolo de la unidad por defecto (solo lectura). */
  default_unit?: string | null
  default_unit_detail?: UnitSummary | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface AnalyteCreate extends AnalyteBase {
  is_active?: boolean
}

export type AnalyteUpdate = Partial<AnalyteBase & { is_active: boolean, activity_reason: string | null }>

export type AnalyteListParams = {
  page?: number
  page_size?: number
  active?: boolean
  /** Búsqueda de texto (`?q=`): insensible a mayúsculas y tildes. */
  q?: string
}

// --------------------------------------------------------------------------
// Result option sets + options
// --------------------------------------------------------------------------

export interface ResultOptionSetBase {
  code: string
  name: string
}

export interface ResultOptionSetRead extends ResultOptionSetBase {
  id: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ResultOptionSetCreate extends ResultOptionSetBase {
  is_active?: boolean
}

export type ResultOptionSetUpdate = Partial<ResultOptionSetBase & { is_active: boolean, activity_reason: string | null }>

export type ResultOptionSetListParams = {
  page?: number
  page_size?: number
  active?: boolean
  /** Búsqueda de texto (`?q=`): insensible a mayúsculas y tildes. */
  q?: string
}

export interface ResultOptionBase {
  code: string
  label: string
  sort_order: number
  is_abnormal?: boolean
}

export interface ResultOptionRead extends ResultOptionBase {
  id: string
  option_set_id: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ResultOptionCreate extends ResultOptionBase {
  is_active?: boolean
}

export type ResultOptionUpdate = Partial<ResultOptionBase & { is_active: boolean, activity_reason: string | null }>

export type ResultOptionListParams = {
  page?: number
  page_size?: number
  active?: boolean
  /** Búsqueda de texto (`?q=`): insensible a mayúsculas y tildes. */
  q?: string
}

// --------------------------------------------------------------------------
// Result templates + versions
// --------------------------------------------------------------------------

export interface ResultTemplateBase {
  code: string
  name: string
  description?: string | null
}

export interface ResultTemplateRead extends ResultTemplateBase {
  id: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ResultTemplateCreate extends ResultTemplateBase {
  is_active?: boolean
}

export type ResultTemplateUpdate = Partial<ResultTemplateBase & { is_active: boolean, activity_reason: string | null }>

export type ResultTemplateListParams = {
  page?: number
  page_size?: number
  active?: boolean
  /** Búsqueda de texto (`?q=`): insensible a mayúsculas y tildes. */
  q?: string
}

export type ResultTemplateVersionStatus = 'draft' | 'published' | 'retired'

export interface ResultTemplateVersionRead {
  id: string
  result_template_id: string
  version_number: number
  status: ResultTemplateVersionStatus
  published_at: string | null
  change_notes: string | null
  report_settings: Record<string, unknown>
  created_at: string
  updated_at: string
}

/**
 * Body de `POST /result-templates/{id}/versions`. Si existe una versión
 * previa, la clona (secciones, analitos y rangos incluidos) y
 * `report_settings` es un override opcional; si es la primera versión,
 * `report_settings` es obligatorio (lo valida el controller, no el schema).
 * El frontend siempre envía `{}` por defecto para cubrir ambos casos.
 */
export interface ResultTemplateVersionCreate {
  report_settings?: Record<string, unknown> | null
  change_notes?: string | null
}

export type ResultTemplateVersionUpdate = ResultTemplateVersionCreate

export type ResultTemplateVersionListParams = {
  page?: number
  page_size?: number
}

// --------------------------------------------------------------------------
// Sections (editable solo en draft)
// --------------------------------------------------------------------------

export interface ResultTemplateSectionRead {
  id: string
  version_id: string
  name: string
  sort_order: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ResultTemplateSectionCreate {
  name: string
  sort_order: number
}

export type ResultTemplateSectionUpdate = Partial<ResultTemplateSectionCreate & { is_active: boolean, activity_reason: string | null }>

/** Listados de secciones / analitos / rangos: solo activos salvo `include_inactive`. */
export type ResultTemplateContentListParams = {
  include_inactive?: boolean
}

// --------------------------------------------------------------------------
// Template analytes (editable solo en draft)
// --------------------------------------------------------------------------

/** Valores de `RESULT_TYPE_VALUES` en el backend (`Literal` en el OpenAPI). */
export const RESULT_TYPES = [
  'numeric',
  'boolean',
  'qualitative',
  'semi_quantitative',
  'titer',
  'text',
  'calculated'
] as const
export type ResultType = typeof RESULT_TYPES[number]

export const RESULT_TYPE_LABELS: Record<ResultType, string> = {
  numeric: 'Numérico',
  boolean: 'Booleano',
  qualitative: 'Cualitativo',
  semi_quantitative: 'Semicuantitativo',
  titer: 'Título (dilución)',
  text: 'Texto',
  calculated: 'Calculado'
}

/**
 * Tipos de resultado que eligen un conjunto de opciones. `titer` se modela
 * como `semi_quantitative` (conjunto semilla `titulos`, de "No reactivo" a
 * ">1:1024"; decisión sujeta a validación del laboratorio).
 */
export const RESULT_TYPES_WITH_OPTION_SET: readonly ResultType[] = ['qualitative', 'semi_quantitative', 'titer']

/** Tipos de resultado con unidad y decimales (obligatorios para publicar). */
export const RESULT_TYPES_WITH_UNIT: readonly ResultType[] = ['numeric', 'calculated']

export interface ResultTemplateAnalyteRead {
  id: string
  version_id: string
  section_id: string | null
  analyte_id: string
  sort_order: number
  result_type: ResultType
  unit_id: string | null
  /** Símbolo de la unidad (solo lectura). */
  unit?: string | null
  unit_detail?: UnitSummary | null
  decimals: number | null
  option_set_id: string | null
  formula: string | null
  is_required: boolean
  is_reportable: boolean
  default_value: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ResultTemplateAnalyteCreate {
  section_id?: string | null
  analyte_id: string
  sort_order: number
  result_type: ResultType
  unit_id?: string | null
  decimals?: number | null
  option_set_id?: string | null
  formula?: string | null
  is_required?: boolean
  is_reportable?: boolean
  default_value?: string | null
}

export type ResultTemplateAnalyteUpdate = Partial<ResultTemplateAnalyteCreate & { is_active: boolean, activity_reason: string | null }>

// --------------------------------------------------------------------------
// Reference ranges (editable solo en draft)
// --------------------------------------------------------------------------

/** Valores de `SEX_VALUES` / `AGE_UNIT_VALUES` en el backend. */
export const REFERENCE_RANGE_SEXES = ['any', 'male', 'female'] as const
export type ReferenceRangeSex = typeof REFERENCE_RANGE_SEXES[number]

export const REFERENCE_RANGE_SEX_LABELS: Record<ReferenceRangeSex, string> = {
  any: 'Cualquiera',
  male: 'Masculino',
  female: 'Femenino'
}

export const REFERENCE_RANGE_AGE_UNITS = ['dias', 'meses', 'anos'] as const
export type ReferenceRangeAgeUnit = typeof REFERENCE_RANGE_AGE_UNITS[number]

export const REFERENCE_RANGE_AGE_UNIT_LABELS: Record<ReferenceRangeAgeUnit, string> = {
  dias: 'Días',
  meses: 'Meses',
  anos: 'Años'
}

export interface ReferenceRangeRead {
  id: string
  template_analyte_id: string
  sex: ReferenceRangeSex
  age_min: number | null
  age_max: number | null
  age_unit: ReferenceRangeAgeUnit | null
  condition: string | null
  low: number | null
  high: number | null
  critical_low: number | null
  critical_high: number | null
  expected_option_id: string | null
  expected_boolean: boolean | null
  display_text: string | null
  interpretation: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ReferenceRangeCreate {
  sex?: ReferenceRangeSex
  age_min?: number | null
  age_max?: number | null
  age_unit?: ReferenceRangeAgeUnit | null
  condition?: string | null
  low?: number | null
  high?: number | null
  critical_low?: number | null
  critical_high?: number | null
  expected_option_id?: string | null
  expected_boolean?: boolean | null
  display_text?: string | null
  interpretation?: string | null
}

export type ReferenceRangeUpdate = Partial<ReferenceRangeCreate & { is_active: boolean, activity_reason: string | null }>

/** Campos de un rango que dependen del `result_type` del analito (el backend rechaza los no admitidos). */
export const REFERENCE_RANGE_TYPED_FIELDS = ['low', 'high', 'critical_low', 'critical_high', 'expected_option_id', 'expected_boolean'] as const
export type ReferenceRangeTypedField = typeof REFERENCE_RANGE_TYPED_FIELDS[number]

/** `details.missing` del 422 de `publish` cuando la plantilla está incompleta. */
export interface ResultTemplatePublishMissingEntry {
  template_analyte_id: string
  result_type: ResultType
  /** `unit_id`, `decimals`, `option_set_id`, `formula`, `reference_ranges`. */
  missing_fields: string[]
  /** Rangos activos con campos que su `result_type` no admite. */
  incompatible_reference_range_ids?: string[]
}

/** `details.inactive` del 422 de `publish`: referencias a elementos desactivados. */
export interface ResultTemplatePublishInactiveEntry {
  template_analyte_id: string
  /** `analyte_id`, `unit_id`, `option_set_id`, `section_id` o `expected_option_id`. */
  field: string
  id: string
}

/**
 * Problema de la fórmula de un analito calculado: `details.problems` del 422
 * al guardar el analito (con `details.field = "formula"`) y
 * `details.invalid_formula` (más `template_analyte_id`) al publicar.
 * `reason`: `syntax`, `unknown_code`, `inactive_code` o `cycle`.
 */
export interface ResultTemplateFormulaProblem {
  reason: string
  message: string
  /** Códigos implicados (desconocidos, inactivos o el recorrido del ciclo). */
  codes: string[]
}

/** `details.invalid_formula` del 422 de `publish` (la clave siempre viene; puede ser `[]`). */
export interface ResultTemplatePublishInvalidFormulaEntry extends ResultTemplateFormulaProblem {
  template_analyte_id: string
}
