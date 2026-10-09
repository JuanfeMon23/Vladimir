<script setup lang="ts">
/**
 * Cabecera de página de un listado: título, descripción y la acción principal
 * (normalmente "Nuevo", que abre el `UiModal` de creación). Reemplaza el
 * bloque "h2 + p + UiButton" repetido en cada `index.vue` de las layers.
 *
 * - `action-label` + `@action`: botón `primary` a la derecha.
 * - `#actions`: acciones a medida (reemplaza el botón por defecto).
 */
withDefaults(
  defineProps<{
    title: string
    description?: string
    /** Texto del botón principal; si se omite (y no hay slot `#actions`), no se muestra botón. */
    actionLabel?: string
  }>(),
  {
    description: undefined,
    actionLabel: undefined
  }
)

const emit = defineEmits<{
  action: []
}>()
</script>

<template>
  <header class="flex flex-wrap items-end justify-between gap-4">
    <div class="min-w-0">
      <h2 class="text-xl font-semibold tracking-tight text-text">
        {{ title }}
      </h2>
      <p v-if="description" class="mt-1 text-sm text-text-muted">
        {{ description }}
      </p>
    </div>

    <div v-if="$slots.actions || actionLabel" class="flex shrink-0 items-center gap-2">
      <slot name="actions">
        <UiButton variant="primary" @click="emit('action')">
          <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path d="M10.75 4.75a.75.75 0 0 0-1.5 0v4.5h-4.5a.75.75 0 0 0 0 1.5h4.5v4.5a.75.75 0 0 0 1.5 0v-4.5h4.5a.75.75 0 0 0 0-1.5h-4.5v-4.5Z" />
          </svg>
          {{ actionLabel }}
        </UiButton>
      </slot>
    </div>
  </header>
</template>
