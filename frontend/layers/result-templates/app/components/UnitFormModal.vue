<script setup lang="ts">
import { z } from 'zod'
import type { UnitRead } from '../types/result-templates'

/** Crear o ver/editar una unidad de medida (catálogo UCUM), en modal desde el listado. */
const props = defineProps<{ entity: UnitRead | null }>()
const emit = defineEmits<{ saved: [] }>()
const open = defineModel<boolean>('open', { required: true })

const schema = z.object({
  code: zRequiredText('El código UCUM es obligatorio.', 64),
  symbol: zRequiredText('El símbolo es obligatorio.', 32),
  name: zRequiredText('El nombre es obligatorio.', 150),
  is_active: z.boolean(),
  activity_reason: zActivityReason()
})

const { submit, isSubmitting, formError } = useZodForm(schema, {
  initialValues: () => ({
    code: props.entity?.code ?? '',
    symbol: props.entity?.symbol ?? '',
    name: props.entity?.name ?? '',
    is_active: props.entity?.is_active ?? true,
    activity_reason: ''
  }),
  resetOn: open
})

const onSubmit = submit(async (values) => {
  if (props.entity) await useUnits().update(props.entity.id, withActivityReason(values, props.entity.is_active))
  else await useUnits().create(withActivityReason(values, undefined))
  emit('saved')
  open.value = false
})
</script>

<template>
  <UiFormModal
    v-model:open="open"
    :activity="entity ? { entityType: 'units', entityId: entity.id } : null"
    :title="entity ? 'Editar unidad' : 'Nueva unidad'"
    :submitting="isSubmitting"
    :form-error="formError"
    :submit-label="entity ? 'Guardar cambios' : 'Crear'"
    @submit="onSubmit"
  >
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <UiFormField name="code" label="Código UCUM" required hint="P. ej. mg/dL, 10*3/uL, mmol/L">
        <UiTextInput />
      </UiFormField>
      <UiFormField name="symbol" label="Símbolo" required hint="Como se imprime en el reporte.">
        <UiTextInput />
      </UiFormField>
      <UiFormField name="name" label="Nombre" required class="sm:col-span-2">
        <UiTextInput />
      </UiFormField>
    </div>
    <UiActiveField label="Activa" :initial="entity?.is_active" />
  </UiFormModal>
</template>
