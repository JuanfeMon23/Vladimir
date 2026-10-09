/**
 * Carga de una pestaña de asignaciones del examen (precondiciones, tipos de
 * muestra, documentos a firmar): al montar, `load` lee el catálogo y lo ya
 * asignado, reinicia el formulario de la pestaña y devuelve las filas a
 * pintar. Expone las filas, la carga y el error, para
 * `<LabTestAssignmentPanel>`.
 */
export function useLabTestAssignmentCatalog<Row>(load: () => Promise<Row[]>, errorMessage: string) {
  const rows = ref<Row[]>([]) as Ref<Row[]>
  const loading = ref(true)
  const loadError = ref<string | null>(null)

  onMounted(async () => {
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
