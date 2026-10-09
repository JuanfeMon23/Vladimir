<script setup lang="ts">
/**
 * Barra de herramientas de un listado: el buscador (`UiSearchInput`) y, en el
 * slot, los filtros del módulo (`UiActiveFilter`, selects…). Una sola
 * estructura para los listados de todas las layers.
 *
 * ```vue
 * <UiListToolbar v-model:search="search" search-placeholder="Buscar por código o nombre…" :searching="loading">
 *   <UiActiveFilter v-model="activeFilter" />
 * </UiListToolbar>
 * ```
 */
withDefaults(
  defineProps<{
    searchPlaceholder?: string
    searchLabel?: string
    /** Hay una búsqueda en curso (spinner en la lupa). */
    searching?: boolean
  }>(),
  {
    searchPlaceholder: undefined,
    searchLabel: undefined,
    searching: false
  }
)

const search = defineModel<string>('search', { required: true })
</script>

<template>
  <div class="flex flex-wrap items-center gap-x-4 gap-y-3">
    <UiSearchInput
      v-model="search"
      class="w-full sm:w-80"
      :placeholder="searchPlaceholder"
      :label="searchLabel"
      :loading="searching"
    />
    <slot />
  </div>
</template>
