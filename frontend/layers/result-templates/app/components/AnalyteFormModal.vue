<script setup lang="ts">
import { z } from 'zod'
import type { AnalyteRead, UnitRead } from '../types/result-templates'

/** Crear o ver/editar un analito del catálogo, en modal desde el listado. */
const props = defineProps<{ entity: AnalyteRead | null }>()
const emit = defineEmits<{ saved: [] }>()
const open = defineModel<boolean>('open', { required: true })

const schema = z.object({
  code: zRequiredText('El código es obligatorio.', 64),
  name: zRequiredText('El nombre es obligatorio.', 150),
  loinc_code: zOptionalText(32),
  default_unit_id: zOptionalId(),
  description: zOptionalText(),
  is_active: z.boolean(),
  activity_reason: zActivityReason()
})

const { submit, isSubmitting, formError } = useZodForm(schema, {
  initialValues: () => ({
    code: props.entity?.code ?? '',
    name: props.entity?.name ?? '',
    loinc_code: props.entity?.loinc_code ?? '',
    default_unit_id: props.entity?.default_unit_id ?? '',
    description: props.entity?.description ?? '',
    is_active: props.entity?.is_active ?? true,
    activity_reason: ''
  }),
  resetOn: open
})

// Unidades (UCUM) para "unidad por defecto": activas, más la ya asignada.
const units = ref<UnitRead[]>([])
const unitsError = ref<string | null>(null)
const unitOptions = computed(() =>
  activeSelectOptions(units.value, unit => `${unit.symbol} — ${unit.name}`, props.entity?.default_unit_id)
)
watch(open, async (isOpen) => {
  if (!isOpen) return
  unitsError.value = null
  try {
    units.value = (await useUnits().list({ page_size: 200 }, { cacheTtl: CATALOG_CACHE_TTL })).items
  } catch (err) {
    unitsError.value = err instanceof Error && err.message ? err.message : 'No se pudieron cargar las unidades.'
  }
}, { immediate: true })

const onSubmit = submit(async (values) => {
  if (props.entity) await useAnalytes().update(props.entity.id, withActivityReason(values, props.entity.is_active))
  else await useAnalytes().create(withActivityReason(values, undefined))
  emit('saved')
  open.value = false
})
</script>

<template>
  <UiFormModal
    v-model:open="open"
    :activity="entity ? { entityType: 'analytes', entityId: entity.id } : null"
    :title="entity ? 'Editar analito' : 'Nuevo analito'"
    size="lg"
    :submitting="isSubmitting"
    :form-error="formError"
    :submit-label="entity ? 'Guardar cambios' : 'Crear'"
    @submit="onSubmit"
  >
    <UiAlert v-if="unitsError" :message="unitsError" />
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <UiFormField name="code" label="Código" required>
        <UiTextInput />
      </UiFormField>
      <UiFormField name="name" label="Nombre" required>
        <UiTextInput />
      </UiFormField>
      <UiFormField name="loinc_code" label="Código LOINC">
        <UiTextInput />
      </UiFormField>
      <UiFormField name="default_unit_id" label="Unidad por defecto (UCUM)">
        <UiSelect :options="unitOptions" empty-label="Sin unidad" />
      </UiFormField>
      <UiFormField name="description" label="Descripción" class="sm:col-span-2">
        <UiTextarea :rows="2" />
      </UiFormField>
    </div>
    <UiActiveField label="Activo" :initial="entity?.is_active" />
  </UiFormModal>
</template>
