<script setup lang="ts">
/**
 * Tarjeta del núcleo (estilo HeroUI Card: superficie blanca, radio grande,
 * sombra suave). Cabecera opcional con `title`/`description` o slot
 * `#header`, acciones a la derecha (`#actions`), cuerpo y pie (`#footer`).
 */
withDefaults(
  defineProps<{
    title?: string
    description?: string
    /** Relleno del cuerpo: `none` para contenido a sangre (tablas, listas). */
    padding?: 'none' | 'sm' | 'md'
    shadow?: 'none' | 'sm' | 'md'
    /** Etiqueta HTML raíz (p. ej. `section`, `article`). */
    as?: string
  }>(),
  {
    title: undefined,
    description: undefined,
    padding: 'md',
    shadow: 'sm',
    as: 'div'
  }
)

const paddingClasses = { none: '', sm: 'p-3', md: 'p-5' } as const
const shadowClasses = { none: 'border border-border', sm: 'shadow-sm', md: 'shadow-md' } as const
</script>

<template>
  <component
    :is="as"
    class="flex flex-col overflow-hidden rounded-lg bg-surface"
    :class="shadowClasses[shadow]"
  >
    <header
      v-if="title || description || $slots.header || $slots.actions"
      class="flex items-start justify-between gap-4 px-5 pt-4"
      :class="padding === 'none' ? 'pb-4' : ''"
    >
      <slot name="header">
        <div class="min-w-0">
          <h3 v-if="title" class="text-base font-semibold text-text">
            {{ title }}
          </h3>
          <p v-if="description" class="mt-0.5 text-sm text-text-muted">
            {{ description }}
          </p>
        </div>
      </slot>
      <div v-if="$slots.actions" class="flex shrink-0 items-center gap-2">
        <slot name="actions" />
      </div>
    </header>

    <div class="flex-1" :class="paddingClasses[padding]">
      <slot />
    </div>

    <footer
      v-if="$slots.footer"
      class="flex items-center justify-end gap-2 border-t border-border px-5 py-3"
    >
      <slot name="footer" />
    </footer>
  </component>
</template>
