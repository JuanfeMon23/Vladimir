/**
 * Tipos del módulo `print-labels`, reflejando el contrato OpenAPI del backend
 * (`app/modules/print_labels/schemas.py`).
 */

export interface PrintLabelBase {
  code: string
  name: string
  description?: string | null
}

export interface PrintLabelRead extends PrintLabelBase {
  id: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface PrintLabelCreate extends PrintLabelBase {
  is_active?: boolean
}

/** Todos los campos opcionales: PATCH parcial. */
export type PrintLabelUpdate = Partial<PrintLabelBase & { is_active: boolean, activity_reason: string | null }>

export interface PrintLabelListParams {
  page?: number
  page_size?: number
  active?: boolean
  /** Búsqueda de texto (`?q=`): insensible a mayúsculas y tildes. */
  q?: string
}

/** Formatos de salida soportados por el backend (`OUTPUT_FORMAT_VALUES`). */
export const PRINT_LABEL_OUTPUT_FORMATS = ['zpl', 'html'] as const
export type PrintLabelOutputFormat = typeof PRINT_LABEL_OUTPUT_FORMATS[number]

export const PRINT_LABEL_OUTPUT_FORMAT_LABELS: Record<PrintLabelOutputFormat, string> = {
  zpl: 'ZPL',
  html: 'HTML'
}

export type PrintLabelVersionStatus = 'draft' | 'published' | 'retired'

export interface PrintLabelVersionRead {
  id: string
  print_label_id: string
  version_number: number
  status: PrintLabelVersionStatus
  published_at: string | null
  change_notes: string | null
  width_mm: number
  height_mm: number
  dpi: number
  output_format: PrintLabelOutputFormat
  barcode_type: string | null
  copies: number
  template_content: string
  placeholders: Record<string, unknown>
  created_at: string
  updated_at: string
}

/**
 * Body de `POST /print-labels/{id}/versions`. Si ya existe una versión
 * previa, el nuevo draft la clona y estos campos son overrides opcionales;
 * si es la primera versión, el backend exige todos salvo `barcode_type` y
 * `change_notes` (regla que valida el controller, no el schema).
 */
export interface PrintLabelVersionCreate {
  width_mm?: number
  height_mm?: number
  dpi?: number
  output_format?: PrintLabelOutputFormat
  barcode_type?: string | null
  copies?: number
  template_content?: string
  placeholders?: Record<string, unknown>
  change_notes?: string | null
}

/** Todos los campos opcionales: PATCH parcial. Solo aplica sobre un draft. */
export type PrintLabelVersionUpdate = PrintLabelVersionCreate

/**
 * Valores de la primera versión de una etiqueta (el backend los exige todos
 * cuando no hay versión previa que clonar). Se editan luego en el editor.
 */
export const PRINT_LABEL_FIRST_VERSION_DEFAULTS: Required<Omit<PrintLabelVersionCreate, 'barcode_type' | 'change_notes'>> = {
  width_mm: 50,
  height_mm: 25,
  dpi: 203,
  output_format: 'zpl',
  copies: 1,
  template_content: '^XA\n^FO20,20^A0N,30,30^FD{{patient_name}}^FS\n^XZ',
  placeholders: { patient_name: 'Nombre del paciente' }
}

export interface PrintLabelVersionListParams {
  page?: number
  page_size?: number
}
