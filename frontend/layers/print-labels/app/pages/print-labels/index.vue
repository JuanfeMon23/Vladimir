<script setup lang="ts">
import type { UiDataTableColumn } from '#andromeda/components/ui/UiDataTable.vue'
import type { PrintLabelRead } from '../../types/print-labels'

definePageMeta({ layout: 'default', leo: { tag: PRINT_LABELS_TAGS.view } })

const createTag = PRINT_LABELS_TAGS.create

// Quien solo consulta ve "Ver"; con algún permiso de cambio, "Ver / Editar".
const canModify = useCan([PRINT_LABELS_TAGS.edit, PRINT_LABELS_TAGS.changeStatus, PRINT_LABELS_TAGS.createVersion, PRINT_LABELS_TAGS.editVersion, PRINT_LABELS_TAGS.publishVersion, PRINT_LABELS_TAGS.retireVersion], 'any')

const printLabelsApi = usePrintLabels()
const activeFilter = ref<boolean | undefined>(undefined)

const search = ref('')

const { rows, total, page, pageSize, loading, loadError, searchTerm, reload } = usePaginatedList({
  fetchPage: (params, { signal }) => printLabelsApi.list({ ...params, active: activeFilter.value }, { signal }),
  search,
  filters: [activeFilter],
  errorMessage: 'No se pudieron cargar las etiquetas.',
  mapError: leoErrorMessage,
  urlSync: useRouteQuerySync(),
  cache: listCache('/print-labels')
})

const modal = useEntityModal<PrintLabelRead>()
useOpenEntityFromQuery(modal, printLabelsApi.get)

const columns: UiDataTableColumn<PrintLabelRead>[] = [
  { key: 'code', label: 'Código' },
  { key: 'name', label: 'Nombre' },
  { key: 'is_active', label: 'Estado' },
  { key: 'id', label: '', class: 'text-right' }
]
</script>

<template>
  <div class="space-y-6">
    <UiPageHeader
      title="Etiquetas de impresión"
      description="Gestión de etiquetas de impresión y sus versiones."
    >
      <template #actions>
        <LeoCan :tag="createTag">
          <UiButton variant="primary" @click="modal.openCreate()">
            Nueva etiqueta
          </UiButton>
        </LeoCan>
      </template>
    </UiPageHeader>

    <UiListToolbar
      v-model:search="search"
      search-placeholder="Buscar por código o nombre…"
      :searching="loading"
    >
      <UiActiveFilter
        id="print-label-active-filter"
        v-model="activeFilter"
        active-label="Activas"
        inactive-label="Inactivas"
      />
    </UiListToolbar>

    <UiAlert v-if="loadError" :message="loadError" />

    <UiDataTable
      :columns="columns"
      :rows="rows"
      :loading="loading"
      :page="page"
      :page-size="pageSize"
      :total="total"
      empty-message="No hay etiquetas registradas."
      :search-term="searchTerm"
      @update:page="page = $event"
      @clear-search="search = ''"
    >
      <template #cell-is_active="{ value }">
        <UiStatusBadge :active="value as boolean" />
      </template>
      <template #cell-id="{ row }">
        <UiButton variant="ghost" size="sm" @click="modal.openEdit(row)">
          {{ canModify ? 'Ver / Editar' : 'Ver' }}
        </UiButton>
      </template>
    </UiDataTable>

    <PrintLabelFormModal v-model:open="modal.open" :entity="modal.entity" @saved="reload" />
  </div>
</template>
