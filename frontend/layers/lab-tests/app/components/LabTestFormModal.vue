<script setup lang="ts">
/**
 * Crear o ver/editar un examen, en modal grande desde el listado. Al editar,
 * el detalle se reparte en pestañas (`UiFormModal tabs`): General (el form
 * principal, con la versión publicada de etiqueta y de plantilla),
 * Precondiciones, Muestras y Documentos (cada una con su propio formulario,
 * que reemplaza el set completo en el backend). Al crear, el examen exige al
 * menos un tipo de muestra: se eligen en la sección "Tipos de muestra" del
 * mismo form (`LabTestSampleTypesDraft`) y viajan en el POST.
 */
import { z } from 'zod'
import type { UiSelectOption } from '#andromeda/components/ui/UiSelect.vue'
import type { UiTab } from '#andromeda/components/ui/UiTabs.vue'
import type { LabTestCatalogOption, LabTestRead } from '../types/lab-tests'

const props = defineProps<{ entity: LabTestRead | null }>()
const emit = defineEmits<{ saved: [] }>()
const open = defineModel<boolean>('open', { required: true })

const labTestsApi = useLabTests()

const TABS: UiTab[] = [
  { key: 'general', label: 'General' },
  { key: 'preconditions', label: 'Precondiciones' },
  { key: 'samples', label: 'Muestras' },
  { key: 'documents', label: 'Documentos' }
]

const schema = z.object({
  code: zRequiredText('El código es obligatorio.', 64),
  name: zRequiredText('El nombre es obligatorio.', 150),
  abbreviation: zOptionalText(32),
  area_id: zRequiredId('Selecciona un área.'),
  method: zOptionalText(150),
  turnaround_hours: zOptionalNumber({ min: 0, integer: true }),
  loinc_code: zOptionalText(32),
  cups_code: zOptionalText(32),
  description: zOptionalText(),
  print_label_version_id: zOptionalId(),
  result_template_version_id: zOptionalId(),
  // Solo al crear: el POST exige los tipos de muestra (≥ 1, un preferido).
  // Al editar se gestionan en la pestaña "Muestras" (PUT) y esto va vacío.
  sample_types: z.array(labTestSampleTypeRowSchema).superRefine((rows, ctx) => {
    if (!props.entity) checkSampleTypeRows(rows, ctx)
  }),
  is_active: z.boolean(),
  activity_reason: zActivityReason()
})

const { submit, isSubmitting, formError } = useZodForm(schema, {
  initialValues: () => ({
    code: props.entity?.code ?? '',
    name: props.entity?.name ?? '',
    abbreviation: props.entity?.abbreviation ?? '',
    area_id: props.entity?.area_id ?? '',
    method: props.entity?.method ?? '',
    turnaround_hours: props.entity?.turnaround_hours ?? '',
    loinc_code: props.entity?.loinc_code ?? '',
    cups_code: props.entity?.cups_code ?? '',
    description: props.entity?.description ?? '',
    print_label_version_id: props.entity?.print_label_version_id ?? '',
    result_template_version_id: props.entity?.result_template_version_id ?? '',
    sample_types: [],
    is_active: props.entity?.is_active ?? true,
    activity_reason: ''
  }),
  // El backend reporta la etiqueta/plantilla inactiva con la clave de la
  // entidad dueña; el error se muestra en el selector de su versión.
  // Los 422 de los tipos de muestra del POST (conteo de preferidos, ids
  // inválidos) se muestran en la sección de tipos de muestra.
  fieldMap: {
    print_label_id: 'print_label_version_id',
    result_template_id: 'result_template_version_id',
    preferred_count: 'sample_types',
    invalid_ids: 'sample_types'
  },
  resetOn: open
})

const isEdit = computed(() => props.entity !== null)

// Al ver/editar, cada grupo de campos exige su permiso (el backend también lo valida).
const canEdit = useCan(LAB_TESTS_TAGS.edit)
const canChangeStatus = useCan(LAB_TESTS_TAGS.changeStatus)
const readOnly = computed(() => isEdit.value && !canEdit.value && !canChangeStatus.value)
/** Los datos son de solo lectura al editar sin `edit`. */
const dataLocked = computed(() => isEdit.value && !canEdit.value)

const onSubmit = submit(async (values) => {
  const { sample_types: sampleTypes, ...fields } = values
  if (props.entity) {
    const body = buildGuardedUpdate(fields, props.entity, { canEdit: canEdit.value, canChangeStatus: canChangeStatus.value })
    if (!body) {
      open.value = false
      return
    }
    await labTestsApi.update(props.entity.id, body)
  } else await labTestsApi.create({ ...withActivityReason(fields, undefined), sample_types: labTestSampleTypesPayload(sampleTypes) })
  emit('saved')
  open.value = false
})

// Áreas: las activas, más la actual del examen aunque esté inactiva. Sin el
// `view` de áreas no se pide el catálogo: se avisa y el selector no se muestra.
const canConsultAreas = useCan(MODULE_VIEW.labAreas.tag)
const areas = ref<LabTestCatalogOption[]>([])
const areasError = ref<string | null>(null)
const areaOptions = computed<UiSelectOption[]>(() =>
  activeSelectOptions(areas.value, area => `${area.name} (${area.code})`, props.entity?.area_id)
)

watch(open, async (isOpen) => {
  if (!isOpen || !canConsultAreas.value) return
  areasError.value = null
  try {
    areas.value = await labTestsApi.listAreaOptions()
  } catch (err) {
    areasError.value = err instanceof Error && err.message ? err.message : 'No se pudieron cargar las áreas.'
  }
}, { immediate: true })
</script>

<template>
  <UiFormModal
    v-model:open="open"
    :activity="entity ? { entityType: 'lab_tests', entityId: entity.id } : null"
    :title="!entity ? 'Nuevo examen' : readOnly ? `Examen: ${entity.name} (solo lectura)` : `Examen: ${entity.name}`"
    :size="entity ? 'xl' : 'lg'"
    :submitting="isSubmitting"
    :form-error="formError"
    :submit-label="readOnly ? 'Cerrar' : entity ? 'Guardar cambios' : 'Crear'"
    :tabs="entity ? TABS : undefined"
    tabs-label="Secciones del examen"
    @submit="onSubmit"
  >
    <UiAlert v-if="!canConsultAreas" variant="warning" :message="noViewMessage(MODULE_VIEW.labAreas)" />
    <UiAlert v-if="areasError" :message="areasError" />
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <UiFormField name="code" label="Código" required>
        <UiTextInput :disabled="dataLocked" />
      </UiFormField>
      <UiFormField name="name" label="Nombre" required>
        <UiTextInput :disabled="dataLocked" />
      </UiFormField>
      <UiFormField name="abbreviation" label="Abreviatura">
        <UiTextInput :disabled="dataLocked" />
      </UiFormField>
      <UiFormField v-if="canConsultAreas" name="area_id" label="Área" required>
        <UiSelect :options="areaOptions" placeholder="Seleccionar área" :disabled="dataLocked" />
      </UiFormField>
      <UiFormField name="method" label="Método">
        <UiTextInput :disabled="dataLocked" />
      </UiFormField>
      <UiFormField name="turnaround_hours" label="Tiempo de entrega (horas)">
        <UiTextInput type="number" min="0" step="1" :disabled="dataLocked" />
      </UiFormField>
      <UiFormField name="loinc_code" label="Código LOINC">
        <UiTextInput :disabled="dataLocked" />
      </UiFormField>
      <UiFormField name="cups_code" label="Código CUPS">
        <UiTextInput :disabled="dataLocked" />
      </UiFormField>
      <UiFormField name="description" label="Descripción" class="sm:col-span-2">
        <UiTextarea :rows="2" :disabled="dataLocked" />
      </UiFormField>
    </div>
    <UiActiveField v-if="!isEdit || canChangeStatus" label="Activo" :initial="entity?.is_active" />

    <UiSection title="Etiqueta de impresión" description="Versión publicada que se imprime para este examen." divided>
      <LabTestVersionPicker
        name="print_label_version_id"
        :module="MODULE_VIEW.printLabels"
        :locked="dataLocked"
        owner-label="Etiqueta"
        owner-placeholder="Sin etiqueta"
        empty-versions-hint="Esta etiqueta no tiene versiones publicadas."
        :load-owners="labTestsApi.listPrintLabelOptions"
        :load-published-versions="labTestsApi.listPublishedPrintLabelVersions"
        :load-version="labTestsApi.getPrintLabelVersion"
      />
    </UiSection>

    <UiSection title="Plantilla de resultados" description="Versión publicada con la que se reportan los resultados." divided>
      <LabTestVersionPicker
        name="result_template_version_id"
        :module="MODULE_VIEW.resultTemplates"
        :locked="dataLocked"
        owner-label="Plantilla"
        owner-placeholder="Sin plantilla"
        empty-versions-hint="Esta plantilla no tiene versiones publicadas."
        :load-owners="labTestsApi.listResultTemplateOptions"
        :load-published-versions="labTestsApi.listPublishedResultTemplateVersions"
        :load-version="labTestsApi.getResultTemplateVersion"
      />
    </UiSection>

    <LabTestSampleTypesDraft v-if="!entity" />

    <template v-if="entity" #preconditions>
      <LabTestPreconditionsEditor :lab-test-id="entity.id" />
    </template>
    <template v-if="entity" #samples>
      <LabTestSampleTypesEditor :lab-test-id="entity.id" />
    </template>
    <template v-if="entity" #documents>
      <LabTestConsentDocumentsEditor :lab-test-id="entity.id" />
    </template>
  </UiFormModal>
</template>
