<script setup lang="ts">
import { z } from 'zod'
import { SAMPLE_SPECIMENS, SAMPLE_SPECIMEN_LABELS } from '../types/samples'
import type { SampleTypeRead } from '../types/samples'

/**
 * Crear (`entity = null`, bajo `sampleId`) o editar un tipo de muestra, en
 * modal anidado dentro del de la muestra.
 */
const props = defineProps<{
  sampleId: string
  entity: SampleTypeRead | null
}>()

const emit = defineEmits<{
  saved: []
}>()

const open = defineModel<boolean>('open', { required: true })

const schema = z.object({
  code: zRequiredText('El código es obligatorio.', 64),
  name: zRequiredText('El nombre es obligatorio.', 150),
  specimen: zRequiredEnum(SAMPLE_SPECIMENS, 'Selecciona un espécimen.'),
  cap_color_hex: zOptionalText(7).refine(
    value => value === null || /^#[0-9a-fA-F]{6}$/.test(value),
    'Usa el formato #RRGGBB, p. ej. #F97316.'
  ),
  additive: zOptionalText(100),
  volume_ml: zOptionalNumber({ min: 0 }),
  storage_temperature: zOptionalText(32),
  stability_hours: zOptionalNumber({ min: 0, integer: true }),
  draw_order: zOptionalNumber({ min: 0, integer: true }),
  collection_instructions: zOptionalText(),
  is_active: z.boolean(),
  activity_reason: zActivityReason()
})

const specimenOptions = toSelectOptions(SAMPLE_SPECIMEN_LABELS)
const isEdit = computed(() => props.entity !== null)

const { submit, isSubmitting, formError } = useZodForm(schema, {
  initialValues: () => ({
    code: props.entity?.code ?? '',
    name: props.entity?.name ?? '',
    specimen: props.entity?.specimen ?? '',
    cap_color_hex: props.entity?.cap_color_hex ?? '',
    additive: props.entity?.additive ?? '',
    volume_ml: props.entity?.volume_ml ?? '',
    storage_temperature: props.entity?.storage_temperature ?? '',
    stability_hours: props.entity?.stability_hours ?? '',
    draw_order: props.entity?.draw_order ?? '',
    collection_instructions: props.entity?.collection_instructions ?? '',
    is_active: props.entity?.is_active ?? true,
    activity_reason: ''
  }),
  resetOn: open
})

const samplesApi = useSamples()

const onSubmit = submit(async (values) => {
  if (props.entity) await samplesApi.updateType(props.entity.id, withActivityReason(values, props.entity.is_active))
  else await samplesApi.createType(props.sampleId, withActivityReason(values, undefined))
  emit('saved')
  open.value = false
})
</script>

<template>
  <UiFormModal
    v-model:open="open"
    :activity="entity ? { entityType: 'sample_types', entityId: entity.id } : null"
    :title="isEdit ? 'Editar tipo de muestra' : 'Nuevo tipo de muestra'"
    size="lg"
    :submitting="isSubmitting"
    :form-error="formError"
    :submit-label="isEdit ? 'Guardar cambios' : 'Crear tipo'"
    @submit="onSubmit"
  >
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <UiFormField name="code" label="Código" required>
        <UiTextInput />
      </UiFormField>
      <UiFormField name="name" label="Nombre" required>
        <UiTextInput />
      </UiFormField>
      <UiFormField name="specimen" label="Espécimen" required>
        <UiSelect :options="specimenOptions" placeholder="Seleccionar espécimen" />
      </UiFormField>
      <UiFormField name="cap_color_hex" label="Color de tapa" hint="Código hex, p. ej. #F97316">
        <UiTextInput placeholder="#RRGGBB" />
      </UiFormField>
      <UiFormField name="additive" label="Aditivo">
        <UiTextInput />
      </UiFormField>
      <UiFormField name="volume_ml" label="Volumen (mL)">
        <UiTextInput type="number" min="0" step="any" />
      </UiFormField>
      <UiFormField name="storage_temperature" label="Temperatura de almacenamiento">
        <UiTextInput />
      </UiFormField>
      <UiFormField name="stability_hours" label="Estabilidad (horas)">
        <UiTextInput type="number" min="0" step="1" />
      </UiFormField>
      <UiFormField name="draw_order" label="Orden de extracción">
        <UiTextInput type="number" min="0" step="1" />
      </UiFormField>
      <UiFormField name="collection_instructions" label="Instrucciones de recolección" class="sm:col-span-2">
        <UiTextarea :rows="3" />
      </UiFormField>
    </div>
    <UiActiveField label="Activo" :initial="entity?.is_active" />
  </UiFormModal>
</template>
