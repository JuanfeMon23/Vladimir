import { useSettingsAdmin } from '#andromeda/composables/useSettingsAdmin'

/**
 * Estado de la pantalla «Ajustes del sistema»: conecta `useSettingsAdmin` de
 * Andromeda con la API de Vladimir, los permisos de la sesión, los avisos y los
 * mensajes de error legibles. Editar exige `vladimir.settings.edit`; los ajustes
 * marcados como de seguridad, además `vladimir.settings.edit-security`.
 */
export function useSettingsScreen() {
  const api = useSettingsApi()
  const toast = useToast()

  return useSettingsAdmin({
    list: api.list,
    history: api.history,
    update: api.update,
    canEdit: useCan(SETTINGS_TAGS.edit),
    canEditSecurity: useCan(SETTINGS_TAGS.editSecurity),
    mapError: leoErrorMessage,
    notify: (kind, message) => toast[kind](message)
  })
}
