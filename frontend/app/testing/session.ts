// `signInWith` (sesión de Leo autenticada con los tags dados) viene de leo-client:
// `import { signInWith } from '#leo-client/testing/session'`.

const allOf = (module: string, verbs: string[]) => verbs.map(verb => `vladimir.${module}.${verb}`)

export const ALL_STAFF_TAGS = allOf('staff', ['view', 'create', 'edit', 'change-status'])
export const ALL_SETTINGS_TAGS = allOf('settings', ['view', 'edit', 'edit-security'])
export const ALL_PRECONDITIONS_TAGS = allOf('preconditions', ['view', 'create', 'edit', 'change-status', 'add-item'])
const VERSIONING = ['create-version', 'edit-version', 'publish-version', 'retire-version']
export const ALL_SAMPLES_TAGS = allOf('samples', ['view', 'create', 'edit', 'change-status', 'add-type'])
export const ALL_PRINT_LABELS_TAGS = allOf('print-labels', ['view', 'create', 'edit', 'change-status', ...VERSIONING])
export const ALL_CONSENT_DOCUMENTS_TAGS = allOf('consent-documents', ['view', 'create', 'edit', 'change-status', ...VERSIONING])
export const ALL_RESULT_TEMPLATES_TAGS = allOf('result-templates', [
  'view', 'create', 'edit', 'change-status', ...VERSIONING, 'edit-content',
  'manage-units', 'manage-analytes', 'manage-option-sets'
])
export const ALL_LAB_TESTS_TAGS = allOf('lab-tests', [
  'view', 'create', 'edit', 'change-status', 'set-preconditions', 'set-sample-types', 'set-consent-documents'
])
/** Los `view` de los módulos que el formulario de examen consulta para sus selectores. */
export const LAB_TEST_SELECTOR_VIEW_TAGS = [
  'vladimir.lab-areas.view', 'vladimir.print-labels.view', 'vladimir.result-templates.view',
  'vladimir.preconditions.view', 'vladimir.samples.view', 'vladimir.consent-documents.view'
]

export const ALL_LAB_AREAS_TAGS = [
  'vladimir.lab-areas.view',
  'vladimir.lab-areas.create',
  'vladimir.lab-areas.edit',
  'vladimir.lab-areas.change-status',
  'vladimir.lab-areas.assign-manager'
]
