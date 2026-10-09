<script setup lang="ts">
/**
 * Pestaña "Precondiciones" del examen: el catálogo de precondiciones activas
 * (raíces e ítems; las ya asignadas aunque se hayan desactivado, marcadas),
 * con un checkbox por fila; las elegidas llevan
 * "obligatoria" y overrides opcionales (cargados de los `*_override` crudos
 * de la asignación). Guarda con `PUT /lab-tests/{id}/preconditions`
 * (reemplaza el set; `sort_order` = orden de la lista: primero las ya
 * asignadas, en su orden).
 */
import { z } from 'zod'
import { LAB_TEST_DURATION_UNIT_LABELS, LAB_TEST_DURATION_UNITS } from '../types/lab-tests'
import type { LabTestPreconditionInput, LabTestPreconditionRead } from '../types/lab-tests'
import type { LabTestAssignmentCatalogEntry, LabTestAssignmentRow } from '../utils/assignmentRows'

const props = defineProps<{ labTestId: string }>()

const labTestsApi = useLabTests()
const durationUnitOptions = toSelectOptions(LAB_TEST_DURATION_UNIT_LABELS)

const rowSchema = z.object({
  precondition_id: z.string(),
  selected: z.boolean(),
  is_mandatory: z.boolean(),
  name_override: zOptionalText(150),
  description_override: zOptionalText(),
  duration_value_override: zOptionalNumber({ min: 0 }),
  duration_unit_override: zOptionalEnum(LAB_TEST_DURATION_UNITS),
  patient_instructions_override: zOptionalText()
})
const schema = z.object({ rows: z.array(rowSchema) })
type RowValues = z.input<typeof rowSchema>

const form = useZodForm(schema, { initialValues: { rows: [] } })
const { submit, isSubmitting, formError, reset } = form

function emptyRow(id: string, selected = false): RowValues {
  return {
    precondition_id: id,
    selected,
    is_mandatory: true,
    name_override: '',
    description_override: '',
    duration_value_override: '',
    duration_unit_override: '',
    patient_instructions_override: ''
  }
}

const catalog = useLabTestAssignmentCatalog<LabTestAssignmentRow>(async () => {
  const [assigned, roots] = await Promise.all([
    labTestsApi.getPreconditions(props.labTestId, { include_inactive: true }),
    labTestsApi.listPreconditionOptions()
  ])
  // Catálogo: raíces e ítems; un ítem se puede agregar si él y su raíz están activos.
  const entries: LabTestAssignmentCatalogEntry[] = []
  for (const root of roots) {
    entries.push({ id: root.id, label: `${root.name} (${root.code})`, isActive: root.is_active })
    for (const item of root.items ?? []) {
      entries.push({ id: item.id, label: `${item.name} (${item.code})`, isActive: item.is_active && root.is_active, indent: true })
    }
  }
  const activeById = new Map(assigned.filter(item => item.is_active).map(item => [item.precondition_id, item]))
  const rows = buildLabTestAssignmentRows(
    assigned.map(item => ({ id: item.precondition_id, linkId: item.id, isActive: item.is_active, sortOrder: item.sort_order, fallbackLabel: item.name })),
    entries
  )
  reset({
    rows: rows.map((row) => {
      const item = activeById.get(row.id)
      return row.assigned && item ? toAssignedRow(item) : emptyRow(row.id)
    })
  })
  return rows
}, 'No se pudo cargar el catálogo de precondiciones.')

function toAssignedRow(item: LabTestPreconditionRead): RowValues {
  return {
    ...emptyRow(item.precondition_id, true),
    is_mandatory: item.is_mandatory,
    name_override: item.name_override ?? '',
    description_override: item.description_override ?? '',
    duration_value_override: item.duration_value_override ?? '',
    duration_unit_override: item.duration_unit_override ?? '',
    patient_instructions_override: item.patient_instructions_override ?? ''
  }
}

const { isSelected, onToggle } = useLabTestAssignmentRows(form, id => emptyRow(id))

const savedMessage = ref<string | null>(null)

const onSubmit = submit(async ({ rows }) => {
  savedMessage.value = null
  const items: LabTestPreconditionInput[] = labTestOrderedAssignmentPayload(rows)
  await labTestsApi.putPreconditions(props.labTestId, items)
  savedMessage.value = 'Precondiciones guardadas.'
})
</script>

<template>
  <LabTestAssignmentPanel
    activity-entity-type="lab_test_preconditions"
    title="Precondiciones"
    description="Marca las precondiciones del examen; los overrides reemplazan el valor del catálogo solo para este examen."
    :items="catalog.rows"
    :loading="catalog.loading"
    :load-error="catalog.loadError"
    :form-error="formError"
    :saved-message="savedMessage"
    :submitting="isSubmitting"
    submit-label="Guardar precondiciones"
    empty-message="No hay precondiciones activas en el catálogo."
    @submit="onSubmit"
  >
    <template #default="{ item: row }">
      <div :class="row.indent ? 'pl-7' : ''">
        <UiFormField :name="`rows[${row.index}].selected`">
          <UiCheckbox :label="row.label" :disabled="!row.selectable" @update:model-value="onToggle(row, $event)" />
        </UiFormField>

        <div v-show="isSelected(row)" class="mt-3 space-y-3 pl-7">
          <UiFormField :name="`rows[${row.index}].is_mandatory`">
            <UiCheckbox label="Obligatoria" />
          </UiFormField>
          <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <UiFormField :name="`rows[${row.index}].name_override`" label="Nombre (override)">
              <UiTextInput />
            </UiFormField>
            <UiFormField :name="`rows[${row.index}].patient_instructions_override`" label="Instrucciones al paciente (override)">
              <UiTextInput />
            </UiFormField>
            <UiFormField :name="`rows[${row.index}].duration_value_override`" label="Duración (override)">
              <UiTextInput type="number" min="0" step="any" />
            </UiFormField>
            <UiFormField :name="`rows[${row.index}].duration_unit_override`" label="Unidad de duración (override)">
              <UiSelect :options="durationUnitOptions" empty-label="Sin override" />
            </UiFormField>
            <UiFormField :name="`rows[${row.index}].description_override`" label="Descripción (override)" class="sm:col-span-2">
              <UiTextarea :rows="2" />
            </UiFormField>
          </div>
        </div>
      </div>
    </template>
  </LabTestAssignmentPanel>
</template>
