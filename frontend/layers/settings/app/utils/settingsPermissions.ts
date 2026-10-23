/**
 * Tags de acción del módulo `settings` (catálogo en Leo; el backend los exige).
 * `vladimir.settings.update` es el evento de auditoría de cada cambio: no se
 * concede ni se muestra, por eso no está aquí.
 */
export const SETTINGS_TAGS = {
  view: 'vladimir.settings.view',
  edit: 'vladimir.settings.edit',
  editSecurity: 'vladimir.settings.edit-security'
} as const
