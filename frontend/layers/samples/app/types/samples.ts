/**
 * Tipos del módulo `samples`, reflejando el contrato OpenAPI del backend.
 *
 * Una muestra (contenedor) agrupa tipos de muestra concretos (`SampleTypeRead`),
 * cada uno con su propio tubo/tapa, aditivo, volumen, etc.
 */

/** Especímenes válidos (`SPECIMEN_VALUES` del backend) con su etiqueta en la interfaz. */
export const SAMPLE_SPECIMEN_LABELS = {
  suero: 'Suero',
  plasma: 'Plasma',
  sangre_total: 'Sangre total',
  orina: 'Orina',
  heces: 'Heces',
  secrecion: 'Secreción',
  otro: 'Otro'
} as const

export type SampleSpecimen = keyof typeof SAMPLE_SPECIMEN_LABELS

export const SAMPLE_SPECIMENS = Object.keys(SAMPLE_SPECIMEN_LABELS) as [SampleSpecimen, ...SampleSpecimen[]]

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

export interface SampleListParams {
  page?: number
  page_size?: number
  active?: boolean
  /** Búsqueda de texto (`?q=`): insensible a mayúsculas y tildes. */
  q?: string
}

export interface SampleTypeBase {
  code: string
  name: string
  specimen: SampleSpecimen
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
