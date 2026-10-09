<script setup lang="ts">
/**
 * Botón del núcleo. Toda acción interactiva (submit, cancelar, eliminar, navegar
 * como botón) pasa por aquí para que el color comunique la semántica de la
 * acción (ver skill `frontend-reusable-ui` → "Sistema de diseño").
 *
 * Estilo HeroUI: radios generosos, leve escala al presionar
 * (`active:scale-[0.97]`), anillo de foco con offset.
 *
 * Si se pasa `to`, se renderiza como `NuxtLink` (navegación con apariencia de
 * botón, p. ej. "Cancelar" o "Nuevo"); si no, como `<button>` real.
 */
export type UiButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost' | 'danger-ghost'
export type UiButtonSize = 'sm' | 'md' | 'lg'

const props = withDefaults(
  defineProps<{
    variant?: UiButtonVariant
    size?: UiButtonSize
    loading?: boolean
    disabled?: boolean
    type?: 'button' | 'submit' | 'reset'
    to?: string
    /** Botón cuadrado solo con icono (requiere `aria-label`). */
    iconOnly?: boolean
  }>(),
  {
    variant: 'primary',
    size: 'md',
    loading: false,
    disabled: false,
    type: 'button',
    to: undefined,
    iconOnly: false
  }
)

const isDisabled = computed(() => props.disabled || props.loading)

/**
 * En loading el `<button>` NO recibe el atributo `disabled`: si el foco está
 * en él (p. ej. tras pulsar Guardar en un `UiModal`) se perdería al `<body>`.
 * Se marca `aria-busy` y se anula el clic (incluido el envío implícito con Enter).
 */
function guardClick(event: MouseEvent) {
  if (props.loading) {
    event.preventDefault()
    event.stopImmediatePropagation()
  }
}

const sizeClasses: Record<UiButtonSize, string> = {
  sm: 'h-8 min-w-8 rounded-sm text-xs gap-1.5',
  md: 'h-10 min-w-10 rounded-md text-sm gap-2',
  lg: 'h-12 min-w-12 rounded-lg text-base gap-2.5'
}

const paddingClasses: Record<UiButtonSize, string> = {
  sm: 'px-3',
  md: 'px-4',
  lg: 'px-6'
}

const variantClasses: Record<UiButtonVariant, string> = {
  primary: 'bg-primary-500 text-text-inverted hover:bg-primary-600 active:bg-primary-700',
  secondary: 'bg-default-100 text-default-800 hover:bg-default-200 active:bg-default-300',
  danger: 'bg-danger-600 text-text-inverted hover:bg-danger-700 active:bg-danger-800',
  ghost: 'bg-transparent text-primary-600 hover:bg-primary-50 active:bg-primary-100',
  'danger-ghost': 'bg-transparent text-danger-600 hover:bg-danger-50 active:bg-danger-100'
}

const spinnerSize = computed<'sm' | 'md'>(() => (props.size === 'lg' ? 'md' : 'sm'))

const classes = computed(() => [
  'inline-flex shrink-0 select-none items-center justify-center whitespace-nowrap font-medium',
  'transition duration-150 ease-out active:scale-[0.97]',
  'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-500',
  'disabled:pointer-events-none disabled:opacity-50 aria-disabled:pointer-events-none aria-disabled:opacity-50 aria-busy:pointer-events-none aria-busy:opacity-80',
  sizeClasses[props.size],
  props.iconOnly ? 'px-0' : paddingClasses[props.size],
  variantClasses[props.variant]
])
</script>

<template>
  <NuxtLink
    v-if="to"
    :to="to"
    :class="classes"
    :aria-disabled="isDisabled || undefined"
    :aria-busy="loading || undefined"
  >
    <UiSpinner v-if="loading" :size="spinnerSize" />
    <slot />
  </NuxtLink>
  <button
    v-else
    :type="type"
    :disabled="disabled"
    @click.capture="guardClick"
    :aria-busy="loading || undefined"
    :class="classes"
  >
    <UiSpinner v-if="loading" :size="spinnerSize" />
    <slot />
  </button>
</template>
