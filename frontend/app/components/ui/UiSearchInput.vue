<script setup lang="ts">
/**
 * Buscador de listados (HeroUI: input "flat" con icono de lupa y botón de
 * limpiar). `v-model` es el término CONFIRMADO: se emite tras `delay` ms sin
 * escribir (por defecto 300), al pulsar Enter o al limpiar (Escape / botón),
 * y es lo que `usePaginatedList({ search })` envía como `q`. Límite de 100
 * caracteres (el máximo del backend). Accesible: `role="search"`, label
 * (oculto) y botón de limpiar con `aria-label`.
 */
import { SEARCH_MAX_LENGTH } from '~/utils/search'

const props = withDefaults(
  defineProps<{
    modelValue: string
    /** Qué se busca, según las columnas del módulo ("Buscar por código o nombre…"). */
    placeholder?: string
    /** Etiqueta accesible (no se ve). */
    label?: string
    /** Retardo del debounce en ms. */
    delay?: number
    /** Hay una búsqueda en curso: la lupa se cambia por un spinner. */
    loading?: boolean
    id?: string
  }>(),
  {
    placeholder: 'Buscar…',
    label: 'Buscar',
    delay: 300,
    loading: false,
    id: undefined
  }
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const generatedId = useId()
const inputId = computed(() => props.id ?? `search-${generatedId}`)

const text = ref(props.modelValue)
const { debounced, flush } = useDebouncedRef(text, props.delay)

// Lo escrito (ya con retardo) sube al padre; si el padre cambia el valor
// (URL, "Limpiar búsqueda"), el input lo refleja al instante.
watch(debounced, (value) => {
  if (value !== props.modelValue) emit('update:modelValue', value)
})
watch(() => props.modelValue, (value) => {
  if (value === text.value) return
  text.value = value
  flush()
})

function clear() {
  text.value = ''
  flush()
}

function onEscape(event: KeyboardEvent) {
  if (!text.value) return
  event.stopPropagation()
  clear()
}
</script>

<template>
  <div role="search" class="relative min-w-0">
    <label :for="inputId" class="sr-only">{{ label }}</label>
    <span class="pointer-events-none absolute inset-y-0 start-3 flex items-center text-default-500">
      <UiSpinner v-if="loading" size="sm" color="primary" label="Buscando" />
      <svg v-else class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
        <path fill-rule="evenodd" d="M9 3.5a5.5 5.5 0 1 0 0 11 5.5 5.5 0 0 0 0-11ZM2 9a7 7 0 1 1 12.452 4.391l3.328 3.329a.75.75 0 1 1-1.06 1.06l-3.329-3.328A7 7 0 0 1 2 9Z" clip-rule="evenodd" />
      </svg>
    </span>
    <input
      :id="inputId"
      v-model="text"
      type="text"
      autocomplete="off"
      enterkeyhint="search"
      :maxlength="SEARCH_MAX_LENGTH"
      :placeholder="placeholder"
      :aria-busy="loading || undefined"
      :class="['h-10 w-full ps-9 pe-10', formControlClasses('flat', false)]"
      @keydown.enter.prevent="flush"
      @keydown.esc="onEscape"
    >
    <UiButton
      v-if="text"
      variant="ghost"
      size="sm"
      icon-only
      class="absolute end-1 top-1"
      aria-label="Limpiar búsqueda"
      @click="clear"
    >
      <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
        <path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z" />
      </svg>
    </UiButton>
  </div>
</template>
