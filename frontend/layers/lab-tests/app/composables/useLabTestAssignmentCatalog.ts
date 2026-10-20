/**
 * Carga de una pestaña de asignaciones del examen (precondiciones, tipos de
 * muestra, documentos a firmar): al montar, `load` lee el catálogo y lo ya
 * asignado, reinicia el formulario de la pestaña y devuelve las filas a
 * pintar. Expone las filas, la carga y el error, para
 * `<LabTestAssignmentPanel>`. Con `enabled` en `false` (el usuario no puede
 * consultar el módulo del catálogo) no pide nada: el panel avisa el permiso
 * que falta.
 */
export function useLabTestAssignmentCatalog<Row>(
  load: () => Promise<Row[]>,
  errorMessage: string,
  enabled: MaybeRefOrGetter<boolean> = true
) {
  const rows = ref<Row[]>([]) as Ref<Row[]>
  const loading = ref(true)
  const loadError = ref<string | null>(null)

  onMounted(async () => {
    if (!toValue(enabled)) {
      loading.value = false
      return
    }
    try {
      rows.value = await load()
    } catch (err) {
      loadError.value = err instanceof Error && err.message ? err.message : errorMessage
    } finally {
      loading.value = false
    }
  })

  return reactive({ rows, loading, loadError })
}
