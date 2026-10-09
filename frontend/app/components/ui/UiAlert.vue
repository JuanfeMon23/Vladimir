<script setup lang="ts">
/**
 * Aviso en línea (estilo HeroUI Alert "flat"): error de carga de un listado,
 * error general de un formulario (`formError` de `useZodForm`), avisos.
 * Reemplaza el `<p class="rounded-md bg-danger-50 ...">` repetido en las layers.
 */
export type UiAlertVariant = 'danger' | 'warning' | 'success' | 'info'

const props = withDefaults(
  defineProps<{
    variant?: UiAlertVariant
    title?: string
    /** Texto del aviso; alternativa al slot por defecto. */
    message?: string | null
  }>(),
  {
    variant: 'danger',
    title: undefined,
    message: undefined
  }
)

const variantClasses: Record<UiAlertVariant, { box: string, icon: string }> = {
  danger: { box: 'bg-danger-50 text-danger-700', icon: 'text-danger-500' },
  warning: { box: 'bg-warning-50 text-warning-800', icon: 'text-warning-600' },
  success: { box: 'bg-success-50 text-success-800', icon: 'text-success-600' },
  info: { box: 'bg-primary-50 text-primary-700', icon: 'text-primary-500' }
}

const role = computed(() => (props.variant === 'danger' || props.variant === 'warning' ? 'alert' : 'status'))
</script>

<template>
  <div
    class="flex items-start gap-3 rounded-lg px-4 py-3 text-sm"
    :class="variantClasses[variant].box"
    :role="role"
  >
    <svg
      class="mt-0.5 h-4 w-4 shrink-0"
      :class="variantClasses[variant].icon"
      viewBox="0 0 20 20"
      fill="currentColor"
      aria-hidden="true"
    >
      <path
        v-if="variant === 'success'"
        fill-rule="evenodd"
        d="M10 18a8 8 0 1 0 0-16 8 8 0 0 0 0 16Zm3.857-9.809a.75.75 0 0 0-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 1 0-1.06 1.061l2.5 2.5a.75.75 0 0 0 1.137-.089l4-5.5Z"
        clip-rule="evenodd"
      />
      <path
        v-else-if="variant === 'info'"
        fill-rule="evenodd"
        d="M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Zm-7-4a1 1 0 1 1-2 0 1 1 0 0 1 2 0ZM9 9a.75.75 0 0 0 0 1.5h.253a.25.25 0 0 1 .244.304l-.459 2.066A1.75 1.75 0 0 0 10.747 15H11a.75.75 0 0 0 0-1.5h-.253a.25.25 0 0 1-.244-.304l.459-2.066A1.75 1.75 0 0 0 9.253 9H9Z"
        clip-rule="evenodd"
      />
      <path
        v-else
        fill-rule="evenodd"
        d="M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Zm-8-5a.75.75 0 0 1 .75.75v4.5a.75.75 0 0 1-1.5 0v-4.5A.75.75 0 0 1 10 5Zm0 10a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z"
        clip-rule="evenodd"
      />
    </svg>
    <div class="min-w-0 flex-1 space-y-0.5">
      <p v-if="title" class="font-semibold">
        {{ title }}
      </p>
      <div>
        <slot>{{ message }}</slot>
      </div>
    </div>
  </div>
</template>
