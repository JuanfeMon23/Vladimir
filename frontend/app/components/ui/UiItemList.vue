<script setup lang="ts" generic="T">
/**
 * Lista compacta de sub-recursos dentro de un detalle (p. ej. ítems de una
 * precondición, tipos de una muestra, historial de encargados de un área):
 * filas con divisor, contenido principal a la izquierda y acciones/estado a
 * la derecha, más los estados de carga y vacío. Para listados paginados de
 * página completa usa `UiDataTable`.
 *
 * `inactive(item)`: filas de elementos desactivados, atenuadas (el chip de
 * estado lo pone la vista en `#trailing`).
 */
withDefaults(
  defineProps<{
    items: T[]
    rowKey: (item: T) => string
    loading?: boolean
    emptyMessage?: string
    inactive?: (item: T) => boolean
  }>(),
  {
    loading: false,
    emptyMessage: 'Sin registros.',
    inactive: undefined
  }
)
</script>

<template>
  <div
    v-if="loading"
    class="flex items-center gap-2 rounded-lg border border-border px-4 py-4 text-sm text-text-muted"
  >
    <UiSpinner size="sm" color="primary" />
    <span>Cargando…</span>
  </div>
  <p
    v-else-if="items.length === 0"
    class="rounded-lg border border-dashed border-border px-4 py-4 text-center text-sm text-text-muted"
  >
    {{ emptyMessage }}
  </p>
  <ul v-else class="divide-y divide-border overflow-hidden rounded-lg border border-border bg-surface">
    <li
      v-for="item in items"
      :key="rowKey(item)"
      class="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 px-4 py-2.5 text-sm transition-colors duration-150 hover:bg-default-50"
    >
      <div class="min-w-0 flex-1" :class="inactive?.(item) ? 'opacity-60' : ''">
        <slot :item="item" />
      </div>
      <div v-if="$slots.trailing" class="flex shrink-0 items-center gap-2">
        <slot name="trailing" :item="item" />
      </div>
    </li>
  </ul>
</template>
