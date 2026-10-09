<script setup lang="ts">
/**
 * Sección "Tipos de muestra" de "Nuevo examen": el recipiente que consume el
 * examen (tubo tapa roja…) es obligatorio al registrarlo (el `POST` los exige).
 * Va DENTRO del form del modal: las filas son el campo `sample_types` de su
 * `useZodForm` (borrador local; el payload viaja en el POST, no hay PUT). Usa
 * las mismas filas que la pestaña "Muestras" del editor
 * (`LabTestSampleTypeRowFields`). Los errores de la lista (≥ 1, un preferido,
 * 422 del backend) salen en el aviso de la sección.
 */
import { useFormContext } from 'vee-validate'
import type { LabTestAssignmentRow } from '../utils/assignmentRows'

const labTestsApi = useLabTests()
const form = useFormContext<{ sample_types: LabTestSampleTypeRowValues[] }>()

const catalog = useLabTestAssignmentCatalog<LabTestAssignmentRow>(async () => {
  const entries = sampleTypeCatalogEntries(await labTestsApi.listSampleOptions())
  const rows = buildLabTestAssignmentRows([], entries)
  // Los valores no se reinician: el form ya está montado y puede traer lo escrito.
  form.setFieldValue('sample_types', rows.map(row => emptySampleTypeRow(row.id)), false)
  return rows
}, 'No se pudo cargar el catálogo de tipos de muestra.')

const { isSelected, onToggle, updateRows } = useLabTestAssignmentRows<LabTestSampleTypeRowValues>({
  get values() { return { rows: form.values.sample_types } },
  setFieldValue: (_field, value, validate) => form.setFieldValue('sample_types', value, validate)
}, emptySampleTypeRow)

function onPreferred(row: LabTestAssignmentRow, checked: boolean) {
  if (!checked) return
  updateRows(rows => preferSampleTypeRow(rows, row.index))
}

const listError = computed(() => form.errors.value.sample_types ?? null)
</script>

<template>
  <UiSection
    title="Tipos de muestra"
    description="Recipiente(s) que consume el examen: marca al menos uno y exactamente uno como preferido."
    divided
  >
    <div class="space-y-3">
      <UiAlert v-if="catalog.loadError" :message="catalog.loadError" />
      <UiAlert v-if="listError" :message="listError" />
      <UiItemList
        :items="catalog.rows"
        :row-key="(row: LabTestAssignmentRow) => row.id"
        :loading="catalog.loading"
        empty-message="No hay tipos de muestra activos en el catálogo. Créalos primero en Muestras."
      >
        <template #default="{ item: row }">
          <LabTestSampleTypeRowFields
            :row="row"
            list-name="sample_types"
            :selected="isSelected(row)"
            @toggle="onToggle(row, $event)"
            @preferred="onPreferred(row, $event)"
          />
        </template>
      </UiItemList>
    </div>
  </UiSection>
</template>
