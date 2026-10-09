<script setup lang="ts">
import type { UiDataTableColumn } from '~/components/ui/UiDataTable.vue'
import type { PrintLabelRead } from '../../types/print-labels'

definePageMeta({ layout: 'default' })

const printLabelsApi = usePrintLabels()
const activeFilter = ref<boolean | undefined>(undefined)

const search = ref('')

const { rows, total, page, pageSize, loading, loadError, searchTerm, reload } = usePaginatedList(
  params => printLabelsApi.list({ ...params, active: activeFilter.value }),
  { resource: '/print-labels', search, filters: [activeFilter], errorMessage: 'No se pudieron cargar las etiquetas.' }
)

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
      action-label="Nueva etiqueta"
      @action="modal.openCreate()"
    />

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
          Ver / Editar
        </UiButton>
      </template>
    </UiDataTable>

    <PrintLabelFormModal v-model:open="modal.open" :entity="modal.entity" @saved="reload" />
  </div>
</template>
