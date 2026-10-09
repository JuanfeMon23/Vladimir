<script setup lang="ts">
/**
 * Campo "Activo" de un `*FormModal` (`is_active`) + motivo opcional del
 * cambio de estado (`activity_reason`). El motivo solo aparece al editar
 * (`initial` definido) y cuando el checkbox quedó distinto del estado
 * guardado. El schema del formulario declara
 * `activity_reason: zActivityReason()` y el submit usa
 * `withActivityReason(values, props.entity?.is_active)`.
 */
import { useFieldValue } from 'vee-validate'

const props = withDefaults(
  defineProps<{
    label?: string
    /** Estado guardado de la entidad; `undefined` al crear. */
    initial?: boolean
  }>(),
  { label: 'Activo', initial: undefined }
)

const isActive = useFieldValue<boolean>('is_active')
const changed = computed(() => props.initial !== undefined && Boolean(isActive.value) !== props.initial)
</script>

<template>
  <div class="space-y-3">
    <UiFormField name="is_active">
      <UiCheckbox :label="label" />
    </UiFormField>
    <UiFormField
      v-if="changed"
      name="activity_reason"
      :label="isActive ? 'Motivo de la reactivación' : 'Motivo de la desactivación'"
      hint="Opcional. Queda en la pestaña Actividad."
    >
      <UiTextInput maxlength="255" />
    </UiFormField>
  </div>
</template>
