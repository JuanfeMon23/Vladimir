<script setup lang="ts" generic="T extends object">
/**
 * Tabla del núcleo con estilo HeroUI: tarjeta blanca con sombra suave,
 * cabecera en píldora gris tenue, filas sin divisores con hover redondeado.
 * Slots de celda por columna (`#cell-<key>`), estado de carga y paginación.
 * Con filas ya mostradas, una nueva carga (página, búsqueda) las conserva
 * atenuadas en vez de reemplazarlas por el spinner (sin parpadeo). Con
 * `search-term` y sin filas muestra "Sin resultados para «x»" + limpiar.
 */
export interface UiDataTableColumn<T> {
  key: keyof T & string
  label: string
  class?: string
}

const props = withDefaults(
  defineProps<{
    columns: UiDataTableColumn<T>[]
    rows: T[]
    loading?: boolean
    rowKey?: (row: T) => string | number
    /** Página actual (1-based). Si se omite junto con total, no se muestra paginación. */
    page?: number
    pageSize?: number
    total?: number
    emptyMessage?: string
    /** Término de búsqueda vigente: sin filas, el vacío es "sin resultados" y ofrece limpiarlo. */
    searchTerm?: string
  }>(),
  {
    loading: false,
    rowKey: (row: T) => String((row as { id?: unknown }).id ?? JSON.stringify(row)),
    page: undefined,
    pageSize: undefined,
    total: undefined,
    emptyMessage: 'No hay registros para mostrar.',
    searchTerm: ''
  }
)

const emit = defineEmits<{
  'update:page': [page: number]
  'clear-search': []
}>()

/** El spinner reemplaza la tabla solo si no hay filas que conservar. */
const showSpinner = computed(() => props.loading && props.rows.length === 0)

const hasPagination = computed(
  () => props.page !== undefined && props.pageSize !== undefined && props.total !== undefined
)
</script>

<template>
  <div class="rounded-lg bg-surface p-3 shadow-sm">
    <div class="overflow-x-auto">
      <table class="w-full border-separate border-spacing-0 text-left text-sm" :aria-busy="loading || undefined">
        <thead>
          <tr>
            <th
              v-for="column in columns"
              :key="column.key"
              scope="col"
              class="h-10 whitespace-nowrap bg-default-100 px-3 text-xs font-semibold text-text-muted first:rounded-l-md last:rounded-r-md"
              :class="column.class"
            >
              {{ column.label }}
            </th>
          </tr>
        </thead>
        <tbody v-if="showSpinner">
          <tr>
            <td :colspan="columns.length" class="px-3 py-12 text-center">
              <div class="flex items-center justify-center gap-2 text-text-muted">
                <UiSpinner size="md" color="primary" />
                <span>Cargando…</span>
              </div>
            </td>
          </tr>
        </tbody>
        <tbody v-else-if="rows.length === 0">
          <tr>
            <td :colspan="columns.length" class="px-3 py-10 text-center text-text-muted">
              <UiSearchEmpty v-if="searchTerm" :term="searchTerm" @clear="emit('clear-search')" />
              <template v-else>
                {{ emptyMessage }}
              </template>
            </td>
          </tr>
        </tbody>
        <TransitionGroup
          v-else
          tag="tbody"
          class="transition-opacity duration-150"
          :class="loading ? 'opacity-60' : ''"
          enter-active-class="transition-opacity duration-150"
          leave-active-class="transition-opacity duration-150"
          enter-from-class="opacity-0"
          leave-to-class="opacity-0"
        >
          <tr
            v-for="row in rows"
            :key="rowKey(row)"
            class="group"
          >
            <td
              v-for="column in columns"
              :key="column.key"
              class="px-3 py-2.5 text-text transition-colors duration-150 first:rounded-l-md last:rounded-r-md group-hover:bg-default-100/70"
              :class="column.class"
            >
              <slot :name="`cell-${column.key}`" :row="row" :value="row[column.key]">
                {{ row[column.key] }}
              </slot>
            </td>
          </tr>
        </TransitionGroup>
      </table>
    </div>

    <UiPagination
      v-if="hasPagination"
      class="mt-2"
      :page="page!"
      :page-size="pageSize!"
      :total="total!"
      @update:page="emit('update:page', $event)"
    />
  </div>
</template>
