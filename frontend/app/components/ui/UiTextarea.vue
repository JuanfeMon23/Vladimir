<script setup lang="ts">
/**
 * Textarea del núcleo, para usarse dentro de `UiFormField`. Mismos modos
 * (controlado / vee-validate) y variantes (flat/bordered) que `UiTextInput`.
 */
import type { UiFormControlVariant } from '~/utils/formControlClasses'

const props = withDefaults(
  defineProps<{
    id?: string
    modelValue?: string | null
    rows?: number
    placeholder?: string
    required?: boolean
    disabled?: boolean
    variant?: UiFormControlVariant
    invalid?: boolean
  }>(),
  {
    id: undefined,
    modelValue: undefined,
    rows: 3,
    placeholder: undefined,
    variant: 'flat',
    invalid: false
  }
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const { controlId, isInvalid, describedBy, value, update, onBlur } = useFormControl<string | null>(
  props,
  v => emit('update:modelValue', v ?? '')
)
</script>

<template>
  <textarea
    :id="controlId"
    :value="value ?? ''"
    :rows="rows"
    :placeholder="placeholder"
    :required="required"
    :disabled="disabled"
    :aria-invalid="isInvalid || undefined"
    :aria-describedby="describedBy"
    :class="['py-2', formControlClasses(variant, isInvalid)]"
    @input="update(($event.target as HTMLTextAreaElement).value)"
    @blur="onBlur"
  />
</template>
