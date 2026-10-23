/**
 * Tipos del módulo `preconditions`, reflejando el contrato OpenAPI del backend
 * (`app/modules/preconditions/schemas.py`).
 *
 * Jerarquía de un nivel: una precondición raíz (`kind: 'precondition'`) agrupa
 * ítems (`kind: 'condition'`) vía `parent_id`. El listado raíz solo trae
 * `kind: 'precondition'`, cada una con sus ítems anidados en `items`; un ítem
 * siempre trae `items: null`.
 */

export type PreconditionKind = 'precondition' | 'condition'

/** Categorías válidas (`CATEGORY_VALUES` del backend) con su etiqueta en la interfaz. */
export const PRECONDITION_CATEGORY_LABELS = {
  ayuno: 'Ayuno',
  dieta: 'Dieta',
  alcohol_sustancias: 'Alcohol y sustancias',
  tabaco: 'Tabaco',
  medicamentos: 'Medicamentos',
  actividad_fisica: 'Actividad física',
  abstinencia_sexual: 'Abstinencia sexual',
  recoleccion_muestra: 'Recolección de muestra',
  horario_toma: 'Horario de toma',
  reposo: 'Reposo',
  higiene: 'Higiene',
  otro: 'Otro'
} as const

export type PreconditionCategory = keyof typeof PRECONDITION_CATEGORY_LABELS

export const PRECONDITION_CATEGORIES = Object.keys(PRECONDITION_CATEGORY_LABELS) as [
  PreconditionCategory,
  ...PreconditionCategory[]
]

/** Unidades de duración válidas (`DURATION_UNIT_VALUES` del backend). */
export const PRECONDITION_DURATION_UNIT_LABELS = {
  minutos: 'Minutos',
  horas: 'Horas',
  dias: 'Días'
} as const

export type PreconditionDurationUnit = keyof typeof PRECONDITION_DURATION_UNIT_LABELS

export const PRECONDITION_DURATION_UNITS = Object.keys(PRECONDITION_DURATION_UNIT_LABELS) as [
  PreconditionDurationUnit,
  ...PreconditionDurationUnit[]
]

/** Etiqueta de una categoría; si el backend devuelve un valor desconocido, el valor tal cual. */
export function preconditionCategoryLabel(category: string): string {
  return (PRECONDITION_CATEGORY_LABELS as Record<string, string>)[category] ?? category
}

export interface PreconditionBase {
  code: string
  name: string
  description?: string | null
  category: string
  duration_value?: number | null
  duration_unit?: string | null
  patient_instructions?: string | null
}

export interface PreconditionRead extends PreconditionBase {
  id: string
  parent_id: string | null
  kind: PreconditionKind
  is_active: boolean
  created_at: string
  updated_at: string
  items: PreconditionRead[] | null
}

export interface PreconditionCreate extends PreconditionBase {
  is_active?: boolean
}

/** Todos los campos opcionales: PATCH parcial. */
export type PreconditionUpdate = Partial<PreconditionBase & { is_active: boolean, activity_reason: string | null }>

export type PreconditionListParams = {
  page?: number
  page_size?: number
  active?: boolean
  /** Búsqueda de texto (`?q=`): insensible a mayúsculas y tildes. */
  q?: string
}
