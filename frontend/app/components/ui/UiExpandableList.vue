<script setup lang="ts" generic="T">
/**
 * Lista de entidades expandibles con hijos anidados (patrón repetido en
 * preconditions — raíz/ítems — y samples — muestra/tipos). Provee el
 * contenedor, el toggle, el chevron, los estados de carga/vacío y la
 * paginación (`UiPagination`, mismas props que `UiDataTable`); cabecera,
 * resumen y panel expandido quedan en slots porque la forma de los hijos
 * difiere entre módulos. Estilo HeroUI: tarjetas con sombra suave, chevron animado.
 */
const props = withDefaults(
  defineProps<{
    items: T[]
    rowKey: (item: T) => string
    loading?: boolean
    emptyMessage?: string
    /** Página actual (1-based). Si se omite junto con total, no se muestra paginación. */
    page?: number
    pageSize?: number
    total?: number
    /** Elementos desactivados: cabecera atenuada. */
    inactive?: (item: T) => boolean
    /** Término de búsqueda vigente: sin elementos, el vacío es "sin resultados" y ofrece limpiarlo. */
    searchTerm?: string
  }>(),
  {
    loading: false,
    emptyMessage: 'No hay registros para mostrar.',
    page: undefined,
    pageSize: undefined,
    total: undefined,
    inactive: undefined,
    searchTerm: ''
  }
)

const emit = defineEmits<{
  'update:page': [page: number]
  'clear-search': []
}>()

/** El spinner reemplaza la lista solo si no hay elementos que conservar. */
const showSpinner = computed(() => props.loading && props.items.length === 0)

const expandedKeys = ref<Set<string>>(new Set())

const hasPagination = computed(
  () => props.page !== undefined && props.pageSize !== undefined && props.total !== undefined && props.total > 0
)

function isExpanded(item: T) {
  return expandedKeys.value.has(props.rowKey(item))
}

function toggle(item: T) {
  const key = props.rowKey(item)
  const next = new Set(expandedKeys.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  expandedKeys.value = next
}
</script>

<template>
  <div class="space-y-3">
    <div
      v-if="showSpinner"
      class="flex items-center justify-center gap-2 rounded-lg bg-surface px-4 py-12 text-sm text-text-muted shadow-sm"
    >
      <UiSpinner size="md" color="primary" />
      <span>Cargando…</span>
    </div>

    <div
      v-else-if="items.length === 0"
      class="rounded-lg bg-surface px-4 py-10 text-center text-sm text-text-muted shadow-sm"
    >
      <UiSearchEmpty v-if="searchTerm" :term="searchTerm" @clear="emit('clear-search')" />
      <p v-else>
        {{ emptyMessage }}
      </p>
    </div>

    <ul
      v-else
      class="space-y-3 transition-opacity duration-150"
      :class="loading ? 'opacity-60' : ''"
      :aria-busy="loading || undefined"
    >
      <li
        v-for="item in items"
        :key="rowKey(item)"
        class="overflow-hidden rounded-lg bg-surface shadow-sm"
      >
        <button
          type="button"
          class="flex w-full items-center justify-between gap-4 px-4 py-3 text-left transition-colors duration-150 hover:bg-default-50 active:bg-default-100 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-primary-500"
          :aria-expanded="isExpanded(item)"
          @click="toggle(item)"
        >
          <div class="flex items-center gap-3" :class="inactive?.(item) ? 'opacity-60' : ''">
            <svg
              class="h-4 w-4 shrink-0 text-default-500 transition-transform duration-200 ease-out"
              :class="{ 'rotate-90': isExpanded(item) }"
              viewBox="0 0 20 20"
              fill="currentColor"
              aria-hidden="true"
            >
              <path fill-rule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clip-rule="evenodd" />
            </svg>
            <slot name="header" :item="item" :expanded="isExpanded(item)" />
          </div>

          <slot name="summary" :item="item" :expanded="isExpanded(item)" />
        </button>

        <div v-if="isExpanded(item)" class="space-y-3 border-t border-border bg-default-50/60 px-4 py-3">
          <slot name="content" :item="item" />
        </div>
      </li>
    </ul>

    <UiPagination
      v-if="hasPagination"
      :page="page!"
      :page-size="pageSize!"
      :total="total!"
      @update:page="emit('update:page', $event)"
    />
  </div>
</template>
