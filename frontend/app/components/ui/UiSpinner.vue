<script setup lang="ts">
/**
 * Spinner reusable del núcleo (estilo HeroUI: pista tenue + arco giratorio).
 * Usado por `UiButton` (estado `loading`, color heredado) y suelto en estados
 * de carga de tabla/página (`color="primary"`, ver `UiDataTable`).
 */
const props = withDefaults(
  defineProps<{
    size?: 'sm' | 'md' | 'lg'
    /** `current` hereda el color del texto; `primary` usa el token primary. */
    color?: 'current' | 'primary'
    label?: string
  }>(),
  {
    size: 'md',
    color: 'current',
    label: 'Cargando'
  }
)

const sizeClass = computed(() => {
  switch (props.size) {
    case 'sm':
      return 'h-4 w-4'
    case 'lg':
      return 'h-8 w-8'
    default:
      return 'h-5 w-5'
  }
})
</script>

<template>
  <svg
    class="animate-spin"
    :class="[sizeClass, color === 'primary' ? 'text-primary-500' : '']"
    viewBox="0 0 24 24"
    fill="none"
    role="status"
    :aria-label="label"
  >
    <circle
      class="opacity-20"
      cx="12"
      cy="12"
      r="9.5"
      stroke="currentColor"
      stroke-width="3"
    />
    <path
      d="M12 2.5a9.5 9.5 0 0 1 9.5 9.5"
      stroke="currentColor"
      stroke-width="3"
      stroke-linecap="round"
    />
  </svg>
</template>
