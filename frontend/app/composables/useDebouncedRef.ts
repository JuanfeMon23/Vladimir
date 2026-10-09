import type { Ref } from 'vue'

/**
 * Copia "con retardo" de un ref: `debounced` toma el valor de `source` tras
 * `delay` ms sin cambios. `flush()` lo aplica de inmediato (Enter, limpiar) y
 * `cancel()` descarta el cambio pendiente. Limpia el temporizador al
 * desmontar el componente.
 */
export function useDebouncedRef<T>(source: Ref<T>, delay = 300) {
  const debounced = ref(source.value) as Ref<T>
  let timer: ReturnType<typeof setTimeout> | undefined

  function cancel() {
    if (timer !== undefined) clearTimeout(timer)
    timer = undefined
  }

  function flush() {
    cancel()
    debounced.value = source.value
  }

  watch(source, () => {
    cancel()
    timer = setTimeout(flush, delay)
  })

  if (getCurrentScope()) onScopeDispose(cancel)

  return { debounced: readonly(debounced) as Readonly<Ref<T>>, flush, cancel }
}
