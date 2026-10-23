import type { VersionRecord } from '~/utils/versioning'

export interface UseVersionEditorOptions<V extends VersionRecord> {
  /** Carga la versión del editor (`null` si no existe). */
  load: () => Promise<V | null | undefined>
  publish: () => Promise<V>
  retire: () => Promise<V>
  /**
   * Se llama con la versión cada vez que cambia (carga, guardado, publicar,
   * retirar): típicamente `reset(valoresDelFormulario(version))`.
   */
  onChange?: (version: V) => void
}

/**
 * Estado común de los editores de versión (página propia
 * `/<modulo>/[id]/versions/[versionId]`): carga de la versión, publicar,
 * retirar (con `UiConfirmModal`) y errores de esas acciones. La página lo
 * pasa a `<UiVersionEditor :editor>`, que pinta la cabecera, el estado y los
 * avisos; el formulario de la versión (con `useZodForm`) queda en la página.
 */
export function useVersionEditor<V extends VersionRecord>(options: UseVersionEditorOptions<V>) {
  const version = ref<V | null>(null) as Ref<V | null>
  const loading = ref(true)
  const loadError = ref<string | null>(null)
  const publishing = ref(false)
  const actionError = ref<string | null>(null)
  /** `details` del último error de publicar/retirar (p. ej. campos faltantes). */
  const actionErrorDetails = ref<unknown>(null)

  const isDraft = computed(() => version.value?.status === 'draft')
  const isPublished = computed(() => version.value?.status === 'published')

  function setVersion(value: V) {
    version.value = value
    options.onChange?.(value)
  }

  /**
   * Actualiza la versión SIN `onChange`: para cambios que no pasan por el
   * formulario (p. ej. adjuntar un archivo) y no deben descartar lo que el
   * usuario lleva escrito.
   */
  function patchVersion(value: V) {
    version.value = value
  }

  async function reload() {
    loading.value = true
    loadError.value = null
    try {
      const found = await options.load()
      if (!found) {
        loadError.value = 'No se encontró la versión solicitada.'
        return
      }
      setVersion(found)
    } catch (err) {
      loadError.value = err instanceof Error && err.message ? err.message : 'No se pudo cargar la versión.'
    } finally {
      loading.value = false
    }
  }

  function captureError(err: unknown, fallback: string) {
    actionError.value = err instanceof Error && err.message ? err.message : fallback
    actionErrorDetails.value = err instanceof LeoApiError ? err.details ?? null : null
  }

  async function publish() {
    publishing.value = true
    actionError.value = null
    actionErrorDetails.value = null
    try {
      setVersion(await options.publish())
    } catch (err) {
      captureError(err, 'No se pudo publicar la versión.')
    } finally {
      publishing.value = false
    }
  }

  const retirement = useConfirmAction(
    async () => {
      actionError.value = null
      actionErrorDetails.value = null
      setVersion(await options.retire())
    },
    { errorMessage: 'No se pudo retirar la versión.', mapError: leoErrorMessage }
  )

  onMounted(reload)

  return reactive({
    version,
    loading,
    loadError,
    isDraft,
    isPublished,
    publishing,
    actionError,
    actionErrorDetails,
    retirement,
    setVersion,
    patchVersion,
    reload,
    publish
  })
}

export type VersionEditorState<V extends VersionRecord = VersionRecord> = ReturnType<typeof useVersionEditor<V>>

/** Lo que `UiVersionEditor` lee del estado (sin los métodos que reciben la versión concreta). */
export type VersionEditorView = Omit<VersionEditorState, 'setVersion' | 'patchVersion'>

