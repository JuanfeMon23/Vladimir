/**
 * Tipos del módulo `staff`, reflejando el contrato OpenAPI del backend
 * (`app/modules/staff/schemas.py`).
 */

export interface StaffBase {
  document_type: string
  document_number: string
  first_name: string
  last_name: string
  email?: string | null
  phone?: string | null
  job_title?: string | null
  professional_license?: string | null
}

export interface StaffRead extends StaffBase {
  id: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface StaffCreate extends StaffBase {
  is_active?: boolean
}

/** Todos los campos opcionales: PATCH parcial. */
export type StaffUpdate = Partial<StaffBase & { is_active: boolean, activity_reason: string | null }>

export interface StaffListParams {
  page?: number
  page_size?: number
  active?: boolean
  /** Búsqueda de texto (`?q=`): insensible a mayúsculas y tildes. */
  q?: string
}
