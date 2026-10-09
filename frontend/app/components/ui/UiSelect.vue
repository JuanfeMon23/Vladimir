<script setup lang="ts">
/**
 * Select nativo del núcleo con estilo HeroUI (chevron propio, variantes
 * flat/bordered), para usarse dentro de `UiFormField`. Mismos modos
 * (controlado / vee-validate) que `UiTextInput`.
 *
 * `class`/`style` van al contenedor; el resto de atributos (`aria-*`,
 * `name`…) al `<select>`.
 *
 * `placeholder` es una opción vacía NO seleccionable (campo obligatorio aún
 * sin elegir); `empty-label` es una opción vacía seleccionable ("Sin
 * sección", "Sin versión"…) para campos opcionales: su valor `''` lo
 * convierten en `null` `zOptionalId`/`zOptionalEnum`.
 */
import type { UiFormControlVariant } from '~/utils/formControlClasses'

export interface UiSelectOption {
  value: string
  label: string
}

defineOptions({ inheritAttrs: false })

const props = withDefaults(
  defineProps<{
    id?: string
    modelValue?: string | null
    options: UiSelectOption[]
    placeholder?: string
    /** Opción vacía seleccionable (campos opcionales). */
    emptyLabel?: string
    required?: boolean
    disabled?: boolean
    variant?: UiFormControlVariant
    invalid?: boolean
  }>(),
  {
    id: undefined,
    modelValue: undefined,
    placeholder: undefined,
    emptyLabel: undefined,
    variant: 'flat',
    invalid: false
  }
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const attrs = useAttrs()
const wrapperAttrs = computed(() => ({ class: attrs.class, style: attrs.style }))
const selectAttrs = computed(() => {
  const { class: _class, style: _style, ...rest } = attrs
  return rest
})

const { controlId, isInvalid, describedBy, value, update, onBlur } = useFormControl<string | null>(
  props,
  v => emit('update:modelValue', v ?? '')
)
</script>

<template>
  <div class="relative flex" v-bind="wrapperAttrs">
    <select
      v-bind="selectAttrs"
      :id="controlId"
      :value="value ?? ''"
      :required="required"
      :disabled="disabled"
      :aria-invalid="isInvalid || undefined"
      :aria-describedby="describedBy"
      :class="['h-10 w-full cursor-pointer appearance-none pr-9', formControlClasses(variant, isInvalid)]"
      @change="update(($event.target as HTMLSelectElement).value)"
      @blur="onBlur"
    >
      <option v-if="emptyLabel" value="">
        {{ emptyLabel }}
      </option>
      <option v-else-if="placeholder" value="" disabled>
        {{ placeholder }}
      </option>
      <option v-for="option in options" :key="option.value" :value="option.value">
        {{ option.label }}
      </option>
    </select>
    <svg
      class="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-default-500"
      viewBox="0 0 20 20"
      fill="currentColor"
      aria-hidden="true"
    >
      <path fill-rule="evenodd" d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z" clip-rule="evenodd" />
    </svg>
  </div>
</template>
