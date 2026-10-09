<script setup lang="ts">
/**
 * Chip de estado (estilo HeroUI Chip, variante "flat": fondo tenue del color
 * semántico + texto oscuro del mismo color, en píldora). Opcionalmente con
 * punto de color (`dot`, variante "dot" de HeroUI).
 */
type Variant = 'success' | 'danger' | 'warning' | 'neutral' | 'primary'

const props = withDefaults(
  defineProps<{
    /** Atajo para estados activo/inactivo (p. ej. `is_active` de un registro). */
    active?: boolean
    /** Color explícito; tiene prioridad sobre `active`. Útil para estados genéricos
     * como draft/published/retired o pendiente/en-progreso/hecho. */
    variant?: Variant
    /** Texto a mostrar; si se omite se infiere de `active`. */
    label?: string
    /** Muestra un punto de color antes del texto. */
    dot?: boolean
  }>(),
  {
    active: undefined,
    variant: undefined,
    label: undefined,
    dot: false
  }
)

const resolvedVariant = computed<Variant>(() => {
  if (props.variant) return props.variant
  if (props.active !== undefined) return props.active ? 'success' : 'danger'
  return 'neutral'
})

const resolvedLabel = computed(() => {
  if (props.label) return props.label
  if (props.active !== undefined) return props.active ? 'Activo' : 'Inactivo'
  return ''
})

const variantClasses: Record<Variant, string> = {
  success: 'bg-success-100 text-success-700',
  danger: 'bg-danger-100 text-danger-700',
  warning: 'bg-warning-100 text-warning-800',
  primary: 'bg-primary-100 text-primary-700',
  neutral: 'bg-default-100 text-default-700'
}

const dotClasses: Record<Variant, string> = {
  success: 'bg-success-500',
  danger: 'bg-danger-500',
  warning: 'bg-warning-500',
  primary: 'bg-primary-500',
  neutral: 'bg-default-400'
}
</script>

<template>
  <span
    class="inline-flex h-6 items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 text-xs font-medium"
    :class="variantClasses[resolvedVariant]"
  >
    <span v-if="dot" class="h-1.5 w-1.5 rounded-full" :class="dotClasses[resolvedVariant]" aria-hidden="true" />
    {{ resolvedLabel }}
  </span>
</template>
