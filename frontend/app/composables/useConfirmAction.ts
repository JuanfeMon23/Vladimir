/** Lo que leen los modales de confirmación del estado de `useConfirmAction`. */
export interface ConfirmActionView {
  open: boolean
  loading: boolean
  error: string | null
  errorCause: unknown
  confirm: () => Promise<void>
}

export interface UseConfirmActionOptions {
  /** Mensaje si el error no trae uno propio. */
  errorMessage?: string
}

/**
 * Estado de una acción que se confirma en `UiConfirmModal` (retirar una
 * versión, desactivar un sub-recurso…): para qué objetivo se pidió, si está
 * abierto, si corre y su error. `confirm()` ejecuta la acción y cierra el
 * modal si sale bien; si falla, deja el error en el modal (`error`, y el
 * error original en `errorCause` para leer sus `details`).
 *
 * ```ts
 * const retirement = useConfirmAction((version: VersionRead) => api.retire(version.id))
 * // fila:  <UiButton variant="danger-ghost" @click="retirement.ask(version)">Retirar</UiButton>
 * // modal: <UiConfirmModal v-model:open="retirement.open" :loading="retirement.loading"
 * //          :error="retirement.error" @confirm="retirement.confirm()" … />
 * // (nada se elimina: para desactivar/reactivar usa `useToggleActive`.)
 * ```
 */
export function useConfirmAction<T>(
  action: (target: T) => Promise<unknown>,
  options: UseConfirmActionOptions = {}
) {
  const open = ref(false)
  const target = shallowRef<T | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  /** Error original de la última ejecución fallida (p. ej. `details` de un `ApiRequestError`). */
  const errorCause = shallowRef<unknown>(null)

  function ask(value: T) {
    target.value = value
    error.value = null
    errorCause.value = null
    open.value = true
  }

  async function confirm() {
    if (target.value === null) return
    loading.value = true
    error.value = null
    errorCause.value = null
    try {
      await action(target.value)
      open.value = false
    } catch (err) {
      errorCause.value = err
      error.value = err instanceof Error && err.message
        ? err.message
        : options.errorMessage ?? 'No se pudo completar la acción.'
    } finally {
      loading.value = false
    }
  }

  return reactive({ open, target, loading, error, errorCause, ask, confirm })
}
