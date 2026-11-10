/**
 * Tipos del módulo `samples`, reflejando el contrato OpenAPI del backend.
 *
 * Una muestra (contenedor) agrupa tipos de muestra concretos (`SampleTypeRead`),
 * cada uno con su propio tubo/tapa, aditivo, volumen, etc.
 */

/**
 * `specimen` es el `code` de un valor del catálogo `specimen-types`
 * (`/catalogs/specimen-types`); las etiquetas salen de la API, no de una lista
 * en el código.
 */

export interface SampleBase {
  code: string
  name: string
  description?: string | null
}

export interface SampleRead extends SampleBase {
  id: string
  is_active: boolean
  created_at: string
  updated_at: string
  types: SampleTypeRead[]
}

export interface SampleCreate extends SampleBase {
  is_active?: boolean
}

/** Todos los campos opcionales: PATCH parcial. */
export type SampleUpdate = Partial<SampleBase & { is_active: boolean, activity_reason: string | null }>

export type SampleListParams = {
  page?: number
  page_size?: number
  active?: boolean
  /** Búsqueda de texto (`?q=`): insensible a mayúsculas y tildes. */
  q?: string
}

export interface SampleTypeBase {
  code: string
  name: string
  specimen: string
  cap_color_hex?: string | null
  additive?: string | null
  volume_ml?: number | null
  storage_temperature?: string | null
  stability_hours?: number | null
  draw_order?: number | null
  collection_instructions?: string | null
}

export interface SampleTypeRead extends SampleTypeBase {
  id: string
  sample_id: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface SampleTypeCreate extends SampleTypeBase {
  is_active?: boolean
}

/** Todos los campos opcionales: PATCH parcial. */
export type SampleTypeUpdate = Partial<SampleTypeBase & { is_active: boolean, activity_reason: string | null }>
