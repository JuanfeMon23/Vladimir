/**
 * Tipos del módulo `lab-areas`, reflejando el contrato OpenAPI del backend
 * (`app/modules/lab_areas/schemas.py`).
 */

export interface ManagerAssignmentRead {
  id: string
  area_id: string
  staff_id: string
  staff_name: string
  start_at: string
  /** `null` = asignación vigente. */
  end_at: string | null
  notes?: string | null
  created_at: string
  updated_at: string
}

export interface LabAreaBase {
  code: string
  name: string
  description?: string | null
}

export interface LabAreaRead extends LabAreaBase {
  id: string
  is_active: boolean
  created_at: string
  updated_at: string
  current_manager: ManagerAssignmentRead | null
}

export interface LabAreaCreate extends LabAreaBase {
  is_active?: boolean
}

/** Todos los campos opcionales: PATCH parcial. */
export type LabAreaUpdate = Partial<LabAreaBase & { is_active: boolean, activity_reason: string | null }>

export type LabAreaListParams = {
  page?: number
  page_size?: number
  active?: boolean
  /** Búsqueda de texto (`?q=`): insensible a mayúsculas y tildes. */
  q?: string
}

export interface AssignManagerPayload {
  staff_id: string
  start_at?: string
  notes?: string | null
}

/**
 * Miembro del personal elegible como encargado (subconjunto de lo que
 * devuelve `GET /staff?active=true`). Tipo propio de la layer: no se importa
 * nada de la layer `staff` (cada layer consulta la API).
 */
export interface LabAreaStaffOption {
  id: string
  first_name: string
  last_name: string
}
