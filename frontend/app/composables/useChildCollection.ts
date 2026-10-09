import type { WatchSource } from 'vue'

export interface UseChildCollectionOptions<C> {
  /** Modal de la entidad padre: al abrirse, la colección se reinicia con `initial()`. */
  open: WatchSource<boolean>
  /** Hijos que ya trae la entidad padre (p. ej. `entity.items`, `entity.types`). */
  initial: () => C[]
  /** Recarga los hijos desde la API (p. ej. `get(id)` del padre). */
  refetch: () => Promise<C[]>
  errorMessage?: string
}

/**
 * Sub-recurso de un detalle en modal (ítems de una precondición, tipos de una
 * muestra…): la lista de hijos, su carga/error, y el estado del modal anidado
 * de crear/editar un hijo (`useEntityModal`). Tras guardar un hijo, llama a
 * `refresh()` para recargar la lista.
 *
 * ```ts
 * const children = useChildCollection({
 *   open,
 *   initial: () => props.entity?.items ?? [],
 *   refetch: async () => (await api.get(props.entity!.id)).items ?? []
 * })
 * // template: <UiItemList :items="children.items" :loading="children.loading" />
 * //           <UiButton @click="children.modal.openCreate()">Agregar</UiButton>
 * ```
 */
export function useChildCollection<C>(options: UseChildCollectionOptions<C>) {
  const items = ref<C[]>([]) as Ref<C[]>
  const loading = ref(false)
  const error = ref<string | null>(null)
  const modal = useEntityModal<C>()

  watch(options.open, (isOpen) => {
    if (!isOpen) return
    items.value = options.initial()
    error.value = null
  }, { immediate: true })

  async function refresh() {
    loading.value = true
    error.value = null
    try {
      items.value = await options.refetch()
    } catch (err) {
      error.value = err instanceof Error && err.message
        ? err.message
        : options.errorMessage ?? 'No se pudo recargar la lista.'
    } finally {
      loading.value = false
    }
  }

  return reactive({ items, loading, error, modal, refresh })
}
