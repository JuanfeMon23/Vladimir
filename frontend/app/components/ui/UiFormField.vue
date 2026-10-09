<script setup lang="ts">
/**
 * Envoltorio de campo: label (estilo HeroUI "label outside"), control en el
 * slot, y mensaje de error o ayuda. Provee a su control hijo `id`,
 * `aria-invalid` y `aria-describedby` (ver `useFormControl`).
 *
 * Dos modos:
 * - Controlado (como antes): el formulario pasa `error` y usa `v-model` en el
 *   control.
 * - vee-validate: con `name`, el campo se registra en el `useForm` /
 *   `useZodForm` del ancestro; el control hijo se enlaza solo (sin
 *   `v-model`) y el error de zod se muestra automáticamente.
 */
import { useField } from 'vee-validate'
import { UI_FORM_FIELD_KEY } from '~/composables/useFormControl'

const props = withDefaults(
  defineProps<{
    label?: string
    /** Id del control asociado. Si se omite, se genera uno. */
    fieldId?: string
    /** Error explícito; tiene prioridad sobre el de vee-validate. */
    error?: string
    hint?: string
    required?: boolean
    /** Ruta del campo en el formulario vee-validate (activa el modo vee-validate). */
    name?: string
  }>(),
  {
    label: undefined,
    fieldId: undefined,
    error: undefined,
    hint: undefined,
    required: false,
    name: undefined
  }
)

const generatedId = useId()
const id = computed(() => props.fieldId ?? generatedId)

const veeField = props.name
  ? useField<unknown>(() => props.name as string, undefined, { syncVModel: false })
  : null

const resolvedError = computed(() => props.error ?? veeField?.errorMessage.value)
const invalid = computed(() => Boolean(resolvedError.value))
const messageId = computed(() => `${id.value}-message`)
const describedBy = computed(() =>
  resolvedError.value || props.hint ? messageId.value : undefined
)

provide(UI_FORM_FIELD_KEY, {
  id,
  invalid,
  describedBy,
  field: veeField
    ? {
        value: veeField.value,
        setValue: (value: unknown) => veeField.setValue(value),
        handleBlur: (event?: Event) => veeField.handleBlur(event, true)
      }
    : undefined
})
</script>

<template>
  <div class="flex flex-col gap-1.5">
    <label
      v-if="label"
      :for="id"
      class="text-sm font-medium transition-colors duration-150"
      :class="invalid ? 'text-danger-600' : 'text-text'"
    >
      {{ label }}
      <span v-if="required" class="text-danger-600" aria-hidden="true">*</span>
    </label>

    <slot />

    <p
      v-if="resolvedError"
      :id="messageId"
      class="text-xs font-medium text-danger-600"
      role="alert"
    >
      {{ resolvedError }}
    </p>
    <p v-else-if="hint" :id="messageId" class="text-xs text-text-muted">
      {{ hint }}
    </p>
  </div>
</template>
