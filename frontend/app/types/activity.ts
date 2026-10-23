/**
 * `entity_type` del historial de activación/desactivación = nombre de la tabla
 * (enum del OpenAPI). Andromeda lo tipa como `string` (`#andromeda/types/activity`);
 * Vladimir lo acota con su propio enum.
 */
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
