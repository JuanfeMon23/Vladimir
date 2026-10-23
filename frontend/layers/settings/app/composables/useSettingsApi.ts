import type { SettingHistoryPage, SettingItem, SettingsListResponse, SettingUpdateBody } from '#andromeda/types/settings'

/**
 * Llamadas a `/settings`: única puerta del módulo a la API. Lanzan
 * `LeoApiError` (con `code` y `details`, que `useSettingsAdmin` interpreta).
 */
export function useSettingsApi() {
  const api = useLeoAppApi()
  const path = (key: string) => `/settings/${encodeURIComponent(key)}`

  return {
    list: () => api.get<SettingsListResponse>('/settings'),
    history: (key: string, page: number) => api.get<SettingHistoryPage>(`${path(key)}/history`, { params: { page } }),
    update: (key: string, body: SettingUpdateBody) => api.put<SettingItem>(path(key), body)
  }
}
