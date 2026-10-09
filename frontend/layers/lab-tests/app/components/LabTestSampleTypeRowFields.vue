<script setup lang="ts">
/**
 * Campos de una fila de tipo de muestra del examen: checkbox del tipo y, si
 * está marcado, "Preferido" + volumen requerido. Compartida por la pestaña
 * "Muestras" (`rows[i]`) y la sección de "Nuevo examen" (`sample_types[i]`);
 * va dentro de un `useZodForm` cuyas filas siguen `LabTestSampleTypeRowValues`.
 */
import type { LabTestAssignmentRow } from '../utils/assignmentRows'

defineProps<{
  row: LabTestAssignmentRow
  /** Ruta de la lista de filas en el formulario (`rows`, `sample_types`). */
  listName: string
  /** La fila está marcada (muestra sus campos). */
  selected: boolean
}>()

const emit = defineEmits<{
  toggle: [checked: boolean]
  preferred: [checked: boolean]
}>()
</script>

<template>
  <div class="flex flex-wrap items-center justify-between gap-x-6 gap-y-3">
    <UiFormField :name="`${listName}[${row.index}].selected`">
      <UiCheckbox :label="row.label" :disabled="!row.selectable" @update:model-value="emit('toggle', $event)" />
    </UiFormField>

    <div v-show="selected" class="flex flex-wrap items-center gap-4">
      <UiFormField :name="`${listName}[${row.index}].is_preferred`">
        <UiCheckbox label="Preferido" @update:model-value="emit('preferred', $event)" />
      </UiFormField>
      <UiFormField :name="`${listName}[${row.index}].required_volume_ml`" label="Volumen (mL)" class="w-32">
        <UiTextInput type="number" min="0" step="any" />
      </UiFormField>
    </div>
  </div>
</template>
