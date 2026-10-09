/**
 * Historial de activación/desactivación (`GET /api/v1/activity`), común a
 * toda entidad con `is_active` (regla de negocio: nada se elimina, se
 * desactiva, y cada cambio de estado queda con fecha-hora y motivo).
 */

/** `entity_type` = nombre de la tabla (enum del OpenAPI). */
export type ActivityEntityType =
  | 'analytes'
  | 'consent_documents'
  | 'lab_areas'
  | 'lab_test_consent_documents'
  | 'lab_test_preconditions'
  | 'lab_test_sample_types'
  | 'lab_tests'
  | 'preconditions'
  | 'print_labels'
  | 'reference_ranges'
  | 'result_option_sets'
  | 'result_options'
  | 'result_template_analytes'
  | 'result_template_sections'
  | 'result_templates'
  | 'sample_types'
  | 'samples'
  | 'staff'
  | 'units'

export type ActivityAction = 'activated' | 'deactivated'

export interface ActivityEventRead {
  id: string
  entity_type: ActivityEntityType
  entity_id: string
  action: ActivityAction
  reason: string | null
  occurred_at: string
}

/** Cuerpo parcial de un PATCH que cambia `is_active` (motivo opcional, ≤ 255). */
export interface ActivityChange {
  is_active: boolean
  activity_reason: string | null
}
