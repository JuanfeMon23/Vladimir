<script setup lang="ts">
/**
 * Pestaña "Muestras" del examen: los tipos de muestra activos (agrupados por
 * muestra; los ya asignados aunque se hayan desactivado, marcados), con un
 * checkbox por fila; los elegidos llevan "preferido" y
 * volumen requerido opcional. Guarda con `PUT /lab-tests/{id}/sample-types`
 * (reemplaza el set). "Exactamente un preferido": marcar uno desmarca los
 * demás; el schema no deja enviar sin tipos ("El examen debe tener al menos
 * un tipo de muestra", sin PUT vacío) ni sin exactamente un preferido (aviso
 * del formulario). El backend las valida también (422 `validation_error`) y se
 * muestran en el mismo aviso.
 */
import { z } from 'zod'
import type { LabTestAssignmentRow } from '../utils/assignmentRows'

const props = defineProps<{ labTestId: string }>()

const labTestsApi = useLabTests()
/** Sin el `view` del módulo del catálogo no se pide nada (el panel avisa el permiso que falta). */
const canConsult = useCan(MODULE_VIEW.samples.tag)

const schema = z.object({ rows: labTestSampleTypeRowsSchema })

const form = useZodForm(schema, { initialValues: { rows: [] } })
const { submit, isSubmitting, formError, reset, errors } = form
/** Error del schema sobre la lista (preferido) o error general del backend. */
const panelError = computed(() => formError.value ?? errors.value.rows ?? null)

const catalog = useLabTestAssignmentCatalog<LabTestAssignmentRow>(async () => {
  const [assigned, samples] = await Promise.all([
    labTestsApi.getSampleTypes(props.labTestId, { include_inactive: true }),
    labTestsApi.listSampleOptions()
  ])
  const entries = sampleTypeCatalogEntries(samples)
  const activeById = new Map(assigned.filter(item => item.is_active).map(item => [item.sample_type_id, item]))
  const rows = buildLabTestAssignmentRows(
    assigned.map(item => ({ id: item.sample_type_id, linkId: item.id, isActive: item.is_active, sortOrder: item.sort_order, fallbackLabel: 'Tipo de muestra' })),
    entries
  )
  reset({
    rows: rows.map((row) => {
      const item = activeById.get(row.id)
      return row.assigned && item
        ? { sample_type_id: row.id, selected: true, is_preferred: item.is_preferred, required_volume_ml: item.required_volume_ml ?? '' }
        : emptySampleTypeRow(row.id)
    })
  })
  return rows
}, 'No se pudo cargar el catálogo de tipos de muestra.', () => canConsult.value)

const { isSelected, onToggle, updateRows } = useLabTestAssignmentRows(form, emptySampleTypeRow)

/** Preferido es exclusivo: al marcar uno se desmarcan los demás. */
function onPreferred(row: LabTestAssignmentRow, checked: boolean) {
  if (!checked) return
  updateRows(rows => preferSampleTypeRow(rows, row.index))
}

const savedMessage = ref<string | null>(null)

const onSubmit = submit(async ({ rows }) => {
  savedMessage.value = null
  await labTestsApi.putSampleTypes(props.labTestId, labTestSampleTypesPayload(rows))
  savedMessage.value = 'Tipos de muestra guardados.'
})
</script>

<template>
  <LabTestAssignmentPanel
    :catalog-module="MODULE_VIEW.samples"
    :save-tag="LAB_TESTS_TAGS.setSampleTypes"
    activity-entity-type="lab_test_sample_types"
    title="Tipos de muestra"
    description="Marca al menos un tipo de muestra (el recipiente); exactamente uno debe ser el preferido."
    :items="catalog.rows"
    :loading="catalog.loading"
    :load-error="catalog.loadError"
    :form-error="panelError"
    :saved-message="savedMessage"
    :submitting="isSubmitting"
    submit-label="Guardar tipos de muestra"
    empty-message="No hay tipos de muestra activos en el catálogo."
    @submit="onSubmit"
  >
    <template #default="{ item: row }">
      <LabTestSampleTypeRowFields
        :row="row"
        list-name="rows"
        :selected="isSelected(row)"
        @toggle="onToggle(row, $event)"
        @preferred="onPreferred(row, $event)"
      />
    </template>
  </LabTestAssignmentPanel>
</template>
