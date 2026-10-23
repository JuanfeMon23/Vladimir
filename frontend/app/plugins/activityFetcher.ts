import type { ActivityEventRead, ActivityFetcher } from '#andromeda/types/activity'

/**
 * Cómo pide Vladimir el historial de activación/desactivación a su API
 * (`GET /activity?entity_type&entity_id`, más reciente primero) para
 * `UiActivityTimeline` / `UiFormModal :activity` / `useActivity` de Andromeda.
 * El cliente se resuelve en cada llamada (no al arrancar) y un fallo llega
 * ya con el mensaje legible.
 */
export default defineNuxtPlugin((nuxtApp) => {
  const fetcher: ActivityFetcher = async ({ entityType, entityId, page, pageSize }) => {
    const api = await nuxtApp.runWithContext(() => useLeoAppApi())
    try {
      const result = await api.get<{ items: ActivityEventRead[], total: number }>('/activity', {
        params: { entity_type: entityType, entity_id: entityId, page, page_size: pageSize }
      })
      return { items: result.items, total: result.total }
    } catch (err) {
      throw new Error(leoErrorMessage(err))
    }
  }
  nuxtApp.vueApp.provide(ACTIVITY_FETCHER_KEY, fetcher)
})
