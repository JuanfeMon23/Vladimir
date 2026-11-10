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

/**
 * `category` y `duration_unit` son el `code` de un valor de los catálogos
 * `precondition-categories` y `duration-units` (`/catalogs/*`); las etiquetas
 * salen de la API, no de una lista en el código.
 */

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
