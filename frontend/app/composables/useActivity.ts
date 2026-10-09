import type { MaybeRefOrGetter } from 'vue'
import type { ActivityEntityType, ActivityEventRead } from '~/types/activity'
import type { Page } from '~/types/api'

export interface UseActivityOptions {
  /** Eventos por página (por defecto 20). */
  pageSize?: number
}

/**
 * Historial de activación/desactivación de una entidad
 * (`GET /activity?entity_type&entity_id`, más reciente primero). Carga al
 * crearse (y cada vez que cambia el id); `loadMore()` agrega la página
 * siguiente. Sin id (`null`) queda vacío y no consulta.
 */
export function useActivity(
  entityType: MaybeRefOrGetter<ActivityEntityType>,
  entityId: MaybeRefOrGetter<string | null | undefined>,
  options: UseActivityOptions = {}
) {
  const api = useApi()
  const pageSize = options.pageSize ?? 20

  const events = ref<ActivityEventRead[]>([])
  const total = ref(0)
  const page = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)
  let requestId = 0

  const hasMore = computed(() => events.value.length < total.value)

  async function fetchPage(next: number) {
    const id = toValue(entityId)
    if (!id) return
    const current = ++requestId
    loading.value = true
    error.value = null
    try {
      const result = await api.get<Page<ActivityEventRead>>('/activity', {
        params: { entity_type: toValue(entityType), entity_id: id, page: next, page_size: pageSize }
      })
      if (current !== requestId) return
      events.value = next === 1 ? result.items : [...events.value, ...result.items]
      total.value = result.total
      page.value = next
    } catch (err) {
      if (current !== requestId) return
      error.value = err instanceof Error && err.message ? err.message : 'No se pudo cargar la actividad.'
    } finally {
      if (current === requestId) loading.value = false
    }
  }

  function reload() {
    events.value = []
    total.value = 0
    page.value = 0
    return fetchPage(1)
  }

  function loadMore() {
    return fetchPage(page.value + 1)
  }

  watch(() => [toValue(entityType), toValue(entityId)], reload, { immediate: true })

  return reactive({ events, total, loading, error, hasMore, reload, loadMore })
}
