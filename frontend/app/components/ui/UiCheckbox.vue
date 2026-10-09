<script setup lang="ts">
/**
 * Checkbox del núcleo (estilo HeroUI: caja redondeada, check animado, leve
 * escala al presionar). Reemplaza el `<input type="checkbox">` plano repetido
 * en los formularios de las layers.
 *
 * - Controlado: `v-model` (boolean).
 * - vee-validate: dentro de `<UiFormField name="...">`, sin `v-model`.
 * El texto va en el slot por defecto o en `label`.
 */
const props = withDefaults(
  defineProps<{
    id?: string
    modelValue?: boolean
    label?: string
    /** Texto secundario bajo el label. */
    description?: string
    disabled?: boolean
    invalid?: boolean
  }>(),
  {
    id: undefined,
    modelValue: undefined,
    label: undefined,
    description: undefined,
    disabled: false,
    invalid: false
  }
)

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const generatedId = useId()
const { controlId, isInvalid, describedBy, value, update, onBlur } = useFormControl<boolean>(
  props,
  v => emit('update:modelValue', v)
)
const inputId = computed(() => controlId.value ?? generatedId)
const checked = computed(() => Boolean(value.value))
</script>

<template>
  <label
    :for="inputId"
    class="group relative inline-flex select-none items-start gap-2.5 text-sm text-text"
    :class="disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'"
  >
    <input
      :id="inputId"
      type="checkbox"
      class="peer sr-only"
      :checked="checked"
      :disabled="disabled"
      :aria-invalid="isInvalid || undefined"
      :aria-describedby="describedBy"
      @change="update(($event.target as HTMLInputElement).checked)"
      @blur="onBlur"
    >
    <span
      class="mt-px flex h-5 w-5 shrink-0 items-center justify-center rounded-sm border-2 transition-all duration-150 group-active:scale-90 peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-primary-500"
      :class="[
        checked
          ? 'border-primary-500 bg-primary-500 text-text-inverted'
          : isInvalid
            ? 'border-danger-500 bg-surface'
            : 'border-default-400 bg-surface group-hover:border-default-500 group-hover:bg-default-100'
      ]"
      aria-hidden="true"
    >
      <svg
        class="h-3.5 w-3.5 transition-all duration-150"
        :class="checked ? 'scale-100 opacity-100' : 'scale-50 opacity-0'"
        viewBox="0 0 16 16"
        fill="none"
        stroke="currentColor"
        stroke-width="2.5"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <path d="M3.5 8.5l3 3 6-7" />
      </svg>
    </span>
    <span v-if="label || description || $slots.default" class="flex flex-col">
      <span :class="isInvalid ? 'text-danger-600' : 'text-text'">
        <slot>{{ label }}</slot>
      </span>
      <span v-if="description" class="text-xs text-text-muted">{{ description }}</span>
    </span>
  </label>
</template>
