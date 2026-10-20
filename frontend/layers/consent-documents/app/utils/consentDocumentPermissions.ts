/** Tags de acción del módulo `consent-documents` (catálogo en Leo; el backend los exige). */
export const CONSENT_DOCUMENTS_TAGS = {
  view: 'vladimir.consent-documents.view',
  create: 'vladimir.consent-documents.create',
  edit: 'vladimir.consent-documents.edit',
  changeStatus: 'vladimir.consent-documents.change-status',
  createVersion: 'vladimir.consent-documents.create-version',
  editVersion: 'vladimir.consent-documents.edit-version',
  publishVersion: 'vladimir.consent-documents.publish-version',
  retireVersion: 'vladimir.consent-documents.retire-version'
} as const

/** Tags del versionado en la forma que esperan `UiVersionSection`/`UiVersionEditor`. */
export const CONSENT_DOCUMENTS_VERSION_PERMISSIONS = {
  create: CONSENT_DOCUMENTS_TAGS.createVersion,
  edit: CONSENT_DOCUMENTS_TAGS.editVersion,
  publish: CONSENT_DOCUMENTS_TAGS.publishVersion,
  retire: CONSENT_DOCUMENTS_TAGS.retireVersion
} as const
