/** Tags de acción del módulo `print-labels` (catálogo en Leo; el backend los exige). */
export const PRINT_LABELS_TAGS = {
  view: 'vladimir.print-labels.view',
  create: 'vladimir.print-labels.create',
  edit: 'vladimir.print-labels.edit',
  changeStatus: 'vladimir.print-labels.change-status',
  createVersion: 'vladimir.print-labels.create-version',
  editVersion: 'vladimir.print-labels.edit-version',
  publishVersion: 'vladimir.print-labels.publish-version',
  retireVersion: 'vladimir.print-labels.retire-version'
} as const

/** Tags del versionado en la forma que esperan `UiVersionSection`/`UiVersionEditor`. */
export const PRINT_LABELS_VERSION_PERMISSIONS = {
  create: PRINT_LABELS_TAGS.createVersion,
  edit: PRINT_LABELS_TAGS.editVersion,
  publish: PRINT_LABELS_TAGS.publishVersion,
  retire: PRINT_LABELS_TAGS.retireVersion
} as const
