<script setup lang="ts">
import { z } from 'zod'
import type { ResultOptionRead, ResultOptionSetRead } from '../types/result-templates'

/**
 * Crear o editar una opción de un conjunto, en el modal anidado del detalle
 * del conjunto (`ResultOptionSetFormModal`).
 */
const props = defineProps<{
  entity: ResultOptionRead | null
  optionSet: ResultOptionSetRead
  /** Orden sugerido para una opción nueva (al final). */
  nextSortOrder?: number
}>()
const emit = defineEmits<{ saved: [] }>()
const open = defineModel<boolean>('open', { required: true })

const schema = z.object({
  code: zRequiredText('El código es obligatorio.', 64),
  label: zRequiredText('La etiqueta es obligatoria.', 150),
  sort_order: zRequiredNumber('El orden es obligatorio.', { min: 0, integer: true }),
  is_abnormal: z.boolean(),
  is_active: z.boolean(),
  activity_reason: zActivityReason()
})

const { submit, isSubmitting, formError } = useZodForm(schema, {
  initialValues: () => ({
    code: props.entity?.code ?? '',
    label: props.entity?.label ?? '',
    sort_order: props.entity?.sort_order ?? props.nextSortOrder ?? 0,
    is_abnormal: props.entity?.is_abnormal ?? false,
    is_active: props.entity?.is_active ?? true,
    activity_reason: ''
  }),
  resetOn: open
})

const onSubmit = submit(async (values) => {
  const api = useResultOptionSets()
  if (props.entity) await api.updateOption(props.entity.id, withActivityReason(values, props.entity.is_active))
  else await api.createOption(props.optionSet.id, withActivityReason(values, undefined))
  emit('saved')
  open.value = false
})
</script>

<template>
  <UiFormModal
    v-model:open="open"
    :activity="entity ? { entityType: 'result_options', entityId: entity.id } : null"
    :title="entity ? 'Editar opción' : 'Nueva opción'"
    :description="`Conjunto «${optionSet.name}».`"
    :submitting="isSubmitting"
    :form-error="formError"
    :submit-label="entity ? 'Guardar cambios' : 'Agregar'"
    @submit="onSubmit"
  >
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-[1fr_1fr_8rem]">
      <UiFormField name="code" label="Código" required>
        <UiTextInput />
      </UiFormField>
      <UiFormField name="label" label="Etiqueta" required>
        <UiTextInput />
      </UiFormField>
      <UiFormField name="sort_order" label="Orden" required>
        <UiTextInput type="number" step="1" min="0" />
      </UiFormField>
    </div>
    <div class="flex flex-wrap gap-6">
      <UiFormField name="is_abnormal">
        <UiCheckbox label="Anormal" description="Se resalta como resultado fuera de lo esperado." />
      </UiFormField>
      <UiActiveField label="Activa" :initial="entity?.is_active" />
    </div>
  </UiFormModal>
</template>
