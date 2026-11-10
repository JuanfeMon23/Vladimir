/**
 * Tipos de los catálogos de categoría (`/api/v1/catalogs/{slug}`), reflejando
 * el OpenAPI del backend (`app/modules/catalogs/schemas.py`). Las listas
 * seleccionables (tipos de documento, categorías, especímenes…) viven en la
 * BD, no en el código: los formularios las piden a la API y los demás módulos
 * las referencian por `code` (un `string` en el contrato).
 */

export const CATALOG_SLUGS = [
  'consent-document-types',
  'consent-signers',
  'duration-units',
  'precondition-kinds',
  'precondition-categories',
  'specimen-types',
  'result-types',
  'sexes',
  'age-units'
] as const
export type CatalogSlug = typeof CATALOG_SLUGS[number]

/** Columnas comunes a todos los catálogos. */
export interface CatalogItem {
  id: string
  code: string
  name: string
  sort_order: number
  is_active: boolean
  created_at: string
  updated_at: string
}

/** `minutes`: minutos que equivale una unidad de duración. */
export interface DurationUnitItem extends CatalogItem {
  minutes: number
}

/** Banderas que gobiernan qué admite y exige un tipo de resultado. */
export interface ResultTypeBehavior {
  /** El valor se elige de un conjunto de opciones (analito: `option_set_id`; rango: `expected_option_id`). */
  uses_option_set: boolean
  /** El rango admite `low`, `high`, `critical_low` y `critical_high`. */
  uses_numeric_range: boolean
  /** El rango admite `expected_boolean`. */
  uses_boolean_range: boolean
  /** `unit_id` y `decimals` son obligatorios para publicar. */
  uses_unit: boolean
  /** `formula` es obligatoria para publicar. */
  uses_formula: boolean
  /** Si el analito es reportable, exige al menos un rango activo para publicar. */
  requires_reference_range: boolean
}

export interface ResultTypeItem extends CatalogItem, ResultTypeBehavior {}

/** `is_wildcard`: fila comodín («cualquiera»); a lo sumo una. */
export interface SexItem extends CatalogItem {
  is_wildcard: boolean
}

/** `days`: días que equivale una unidad de edad. */
export interface AgeUnitItem extends CatalogItem {
  days: number
}

export interface CatalogItemBySlug {
  'consent-document-types': CatalogItem
  'consent-signers': CatalogItem
  'duration-units': DurationUnitItem
  'precondition-kinds': CatalogItem
  'precondition-categories': CatalogItem
  'specimen-types': CatalogItem
  'result-types': ResultTypeItem
  'sexes': SexItem
  'age-units': AgeUnitItem
}

/** Cuerpo del POST: el `code` se fija al crear y no se edita (otras tablas lo referencian). */
export type CatalogCreate<S extends CatalogSlug = CatalogSlug> =
  Omit<CatalogItemBySlug[S], 'id' | 'created_at' | 'updated_at' | 'is_active' | 'sort_order'>
  & { sort_order?: number, is_active?: boolean }

/** Todos los campos opcionales: PATCH parcial (sin `code`). */
export type CatalogUpdate<S extends CatalogSlug = CatalogSlug> =
  Partial<Omit<CatalogItemBySlug[S], 'id' | 'code' | 'created_at' | 'updated_at'>>
  & { activity_reason?: string | null }
