import type { Ref, WatchSource } from 'vue'
import type { ListRequestParams, Page } from '~/types/api'
import { cacheKey, isCacheFresh, LIST_CACHE_TTL, stampCache, type CacheStamp } from '~/utils/requestCache'
import { normalizeSearchTerm } from '~/utils/search'

export interface UsePaginatedListOptions {
  /** Tamaño de página (por defecto 20). */
  pageSize?: number
  /** Mensaje si el error no trae uno propio. */
  errorMessage?: string
  /** Filtros del listado: al cambiar, vuelve a la página 1 y recarga. */
  filters?: WatchSource[]
  /** Cargar al montar (por defecto `true`). */
  immediate?: boolean
  /**
   * Texto del buscador (el valor ya confirmado, p. ej. el `v-model` de
   * `UiSearchInput`). Se envía como `q` (normalizado; vacío = no se envía) y
   * al cambiar vuelve a la página 1.
   */
  search?: Ref<string>
  /**
   * Recurso del listado (`'/staff'`). Activa la carga inicial en el servidor
   * (SSR, `useAsyncData`) y la caché de páginas/búsquedas recientes; el
   * recurso es también el prefijo que invalidan las mutaciones de `useApi`.
   * Sin él, el listado carga al montar y sin caché.
   */
  resource?: string
  /** Vigencia de la caché en ms (por defecto 30 s). */
  cacheTtl?: number
  /** Sincronizar `q` y `page` con la URL (por defecto `true` si hay `search`). */
  urlSync?: boolean
}

/** Contador para listados sin `resource` (sin SSR ni caché), que no deben compartir clave. */
let anonymousLists = 0

function parsePageParam(value: unknown): number {
  const n = typeof value === 'string' ? Number(value) : NaN
  return Number.isInteger(n) && n >= 1 ? n : 1
}

/**
 * Estado de un listado paginado (página, filas, total, carga y error de
 * carga), repetido en cada `index.vue` de las layers. El `fetchPage` recibe
 * `{ page, page_size, q? }` y lee él mismo los filtros, p. ej.:
 *
 * ```ts
 * const search = ref('')
 * const activeFilter = ref<boolean | undefined>()
 * const { rows, total, page, pageSize, loading, loadError, searchTerm, reload } = usePaginatedList(
 *   params => useStaff().list({ ...params, active: activeFilter.value }),
 *   { resource: '/staff', search, filters: [activeFilter], errorMessage: 'No se pudo cargar el personal.' }
 * )
 * ```
 *
 * - Con `resource`, la primera carga ocurre en el servidor (llega en el HTML y
 *   se hidrata sin repetir la petición) y las páginas/búsquedas recientes se
 *   sirven de la caché del navegador; `reload()` siempre refresca.
 * - Con `search`, `q` y `page` viajan en la URL (`router.replace`) y se leen
 *   al arrancar, para compartir el enlace.
 * - Mientras carga conserva las filas anteriores (`loading` en `true`), no
 *   repite una petición con los mismos parámetros e ignora respuestas viejas
 *   si se dispara otra antes de que terminen.
 */
export function usePaginatedList<T>(
  fetchPage: (params: ListRequestParams) => Promise<Page<T>>,
  options: UsePaginatedListOptions = {}
) {
  const { search, resource } = options
  const syncUrl = options.urlSync ?? !!search
  const route = syncUrl ? useRoute() : undefined
  const router = syncUrl ? useRouter() : undefined
  const ttl = options.cacheTtl ?? LIST_CACHE_TTL

  // Estado inicial desde la URL (el servidor ve la misma que el navegador).
  const page = ref(route ? parsePageParam(route.query.page) : 1)
  if (search && route && typeof route.query.q === 'string') search.value = normalizeSearchTerm(route.query.q)

  const pageSize = ref(options.pageSize ?? 20)
  const searchTerm = computed(() => normalizeSearchTerm(search?.value))

  function messageOf(err: unknown) {
    return err instanceof Error && err.message
      ? err.message
      : options.errorMessage ?? 'No se pudo cargar el listado.'
  }

  // Cambiar filtros/término vuelve a la página 1. Síncrono y declarado ANTES de
  // `useAsyncData` para que la clave ya tenga la página 1 cuando él la lee (una
  // sola petición).
  const resetSources: WatchSource[] = [...(options.filters ?? []), ...(search ? [searchTerm] : [])]
  if (resetSources.length) watch(resetSources, () => { page.value = 1 }, { flush: 'sync' })

  // La clave determina qué se pide y qué se reutiliza: cambia con página,
  // término y filtros (`useAsyncData` vuelve a cargar y descarta respuestas
  // viejas). Sin `resource` cada instancia tiene la suya y no hay caché.
  const anonymous = `anon-${++anonymousLists}`
  const key = computed(() => `list:${cacheKey(resource ?? anonymous, {
    page: page.value,
    page_size: pageSize.value,
    q: searchTerm.value,
    filters: (options.filters ?? []).map(filter => toValue(filter))
  })}`)

  // Primera carga en el servidor (llega en el HTML y se hidrata sin repetir la
  // petición); después, lo pedido hace menos de `ttl` se reutiliza salvo
  // `reload()`. Lo guardado lleva el sello de `stampCache` para que una
  // mutación (`invalidateCaches`) lo deje viejo.
  const { data, status, error, refresh } = useAsyncData(
    key,
    async () => {
      const stamp = stampCache()
      try {
        const result = await fetchPage({
          page: page.value,
          page_size: pageSize.value,
          ...(searchTerm.value ? { q: searchTerm.value } : {})
        })
        return { result, stamp }
      } catch (err) {
        throw new Error(messageOf(err))
      }
    },
    {
      immediate: options.immediate ?? true,
      getCachedData: (cachedKey, nuxtApp, ctx) => {
        if (!resource || ctx.cause === 'refresh:manual') return undefined
        const cached = nuxtApp.payload.data[cachedKey] as { result: Page<T>, stamp: CacheStamp } | undefined
        return cached && (nuxtApp.isHydrating || isCacheFresh(cached.stamp, ttl)) ? cached : undefined
      }
    }
  )

  // Mientras carga otra página/búsqueda se conservan las filas anteriores
  // (`data` queda vacío al cambiar de clave). Calculado, no copiado por un
  // watcher: en el servidor los watchers no corren y el HTML ya trae las filas.
  const previous = shallowRef<Page<T> | null>(null)
  const current = computed(() => data.value?.result ?? previous.value)
  watch(data, (value) => { if (value) previous.value = value.result })
  const rows = computed(() => current.value?.items ?? []) as ComputedRef<T[]>
  const total = computed(() => current.value?.total ?? 0)
  const loading = computed(() => status.value === 'pending')
  const loadError = computed(() => (error.value ? error.value.message : null))

  const reload = async () => { await refresh() }

  if (route && router) {
    watch([page, searchTerm], () => {
      const { q: _q, page: _page, ...rest } = route.query
      const query = {
        ...rest,
        ...(searchTerm.value ? { q: searchTerm.value } : {}),
        ...(page.value > 1 ? { page: String(page.value) } : {})
      }
      router.replace({ query })
    })
  }

  return { page, pageSize, rows, total, loading, loadError, searchTerm, reload }
}
