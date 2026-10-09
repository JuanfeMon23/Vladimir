<script setup lang="ts">
/**
 * Input de texto del núcleo, para usarse dentro de `UiFormField`. Soporta
 * `type` nativo (text, email, number, date…). Modo controlado (`v-model`) o
 * enlazado a vee-validate vía `<UiFormField name="...">` (ver `useFormControl`).
 * Estilo HeroUI: variante `flat` (por defecto) o `bordered`.
 */
import type { UiFormControlVariant } from '~/utils/formControlClasses'

const props = withDefaults(
  defineProps<{
    id?: string
    modelValue?: string | number | null
    type?: string
    placeholder?: string
    required?: boolean
    disabled?: boolean
    min?: string | number
    max?: string | number
    step?: string | number
    variant?: UiFormControlVariant
    invalid?: boolean
  }>(),
  {
    id: undefined,
    modelValue: undefined,
    type: 'text',
    placeholder: undefined,
    min: undefined,
    max: undefined,
    step: undefined,
    variant: 'flat',
    invalid: false
  }
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const { controlId, isInvalid, describedBy, value, update, onBlur } = useFormControl<string | number | null>(
  props,
  v => emit('update:modelValue', String(v ?? ''))
)
</script>

<template>
  <input
    :id="controlId"
    :value="value ?? ''"
    :type="type"
    :placeholder="placeholder"
    :required="required"
    :disabled="disabled"
    :min="min"
    :max="max"
    :step="step"
    :aria-invalid="isInvalid || undefined"
    :aria-describedby="describedBy"
    :class="['h-10', formControlClasses(variant, isInvalid)]"
    @input="update(($event.target as HTMLInputElement).value)"
    @blur="onBlur"
  >
</template>
