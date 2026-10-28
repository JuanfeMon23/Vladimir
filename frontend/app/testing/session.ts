// `signInWith` (sesión de Leo autenticada con los tags dados) viene de leo-client:
// `import { signInWith } from '#leo-client/testing/session'`.

import permissions from '../generated/permissions.json'
import { MODULE_VIEW } from '../utils/moduleAccess'

/** Todos los tags asignables de un módulo, derivados del contrato del backend. */
const allOf = (module: string): string[] => {
  const found = permissions.modules.find(m => m.slug === module)
  if (!found) throw new Error(`Módulo inexistente en generated/permissions.json: ${module}`)
  return found.actions.filter(action => action.assignable).map(action => action.tag)
}

export const ALL_STAFF_TAGS = allOf('staff')
export const ALL_SETTINGS_TAGS = allOf('settings')
export const ALL_PRECONDITIONS_TAGS = allOf('preconditions')
export const ALL_SAMPLES_TAGS = allOf('samples')
export const ALL_PRINT_LABELS_TAGS = allOf('print-labels')
export const ALL_CONSENT_DOCUMENTS_TAGS = allOf('consent-documents')
export const ALL_RESULT_TEMPLATES_TAGS = allOf('result-templates')
export const ALL_LAB_TESTS_TAGS = allOf('lab-tests')
export const ALL_LAB_AREAS_TAGS = allOf('lab-areas')
/** Los `view` de los módulos que el formulario de examen consulta para sus selectores. */
export const LAB_TEST_SELECTOR_VIEW_TAGS: string[] = Object.values(MODULE_VIEW).map(module => module.tag)
