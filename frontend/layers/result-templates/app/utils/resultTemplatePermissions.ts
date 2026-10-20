/** Tags de acción del módulo `result-templates` (catálogo en Leo; el backend los exige). */
export const RESULT_TEMPLATES_TAGS = {
  view: 'vladimir.result-templates.view',
  create: 'vladimir.result-templates.create',
  edit: 'vladimir.result-templates.edit',
  changeStatus: 'vladimir.result-templates.change-status',
  createVersion: 'vladimir.result-templates.create-version',
  editVersion: 'vladimir.result-templates.edit-version',
  publishVersion: 'vladimir.result-templates.publish-version',
  retireVersion: 'vladimir.result-templates.retire-version',
  editContent: 'vladimir.result-templates.edit-content',
  manageUnits: 'vladimir.result-templates.manage-units',
  manageAnalytes: 'vladimir.result-templates.manage-analytes',
  manageOptionSets: 'vladimir.result-templates.manage-option-sets'
} as const

/** Tags del versionado en la forma que esperan `UiVersionSection`/`UiVersionEditor`. */
export const RESULT_TEMPLATES_VERSION_PERMISSIONS = {
  create: RESULT_TEMPLATES_TAGS.createVersion,
  edit: RESULT_TEMPLATES_TAGS.editVersion,
  publish: RESULT_TEMPLATES_TAGS.publishVersion,
  retire: RESULT_TEMPLATES_TAGS.retireVersion
} as const
