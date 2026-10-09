<script setup lang="ts">
/**
 * Sección con título dentro de un detalle (típicamente en el `#extra` de
 * `UiFormModal`): título `h3` enlazado por `aria-labelledby`, descripción o
 * dato a la derecha (`#aside`), acciones (`#actions`) y contenido. Sin
 * tarjeta propia (para eso, `UiCard`); con `divided` agrega el separador
 * superior que la distingue del formulario principal.
 */
withDefaults(
  defineProps<{
    title: string
    description?: string
    divided?: boolean
  }>(),
  {
    description: undefined,
    divided: false
  }
)

const titleId = useId()
</script>

<template>
  <section class="space-y-3" :class="divided ? 'border-t border-border pt-5' : ''" :aria-labelledby="titleId">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <div class="min-w-0">
        <h3 :id="titleId" class="text-base font-semibold text-text">
          {{ title }}
        </h3>
        <p v-if="description" class="mt-0.5 text-sm text-text-muted">
          {{ description }}
        </p>
      </div>
      <div v-if="$slots.aside || $slots.actions" class="flex shrink-0 items-center gap-3">
        <slot name="aside" />
        <slot name="actions" />
      </div>
    </div>
    <slot />
  </section>
</template>
