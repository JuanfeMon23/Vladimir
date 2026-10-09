<script setup lang="ts">
import type { UiDataTableColumn } from '~/components/ui/UiDataTable.vue'
import type { ResultOptionSetRead } from '../../types/result-templates'

definePageMeta({ layout: 'default' })

const optionSetsApi = useResultOptionSets()
const activeFilter = ref<boolean | undefined>(undefined)

const search = ref('')

const { rows, total, page, pageSize, loading, loadError, searchTerm, reload } = usePaginatedList(
  params => optionSetsApi.list({ ...params, active: activeFilter.value }),
  { resource: '/result-option-sets', search, filters: [activeFilter], errorMessage: 'No se pudieron cargar los conjuntos de opciones.' }
)

const modal = useEntityModal<ResultOptionSetRead>()

const columns: UiDataTableColumn<ResultOptionSetRead>[] = [
  { key: 'code', label: 'Código' },
  { key: 'name', label: 'Nombre' },
  { key: 'is_active', label: 'Estado' },
  { key: 'id', label: '', class: 'text-right' }
]
</script>

<template>
  <div class="space-y-6">
    <UiPageHeader
      title="Conjuntos de opciones"
      description="Catálogos de opciones para analitos cualitativos y semicuantitativos."
      action-label="Nuevo conjunto"
      @action="modal.openCreate()"
    />

    <UiListToolbar
      v-model:search="search"
      search-placeholder="Buscar por código o nombre…"
      :searching="loading"
    >
      <UiActiveFilter
        id="result-option-set-active-filter"
        v-model="activeFilter"
        active-label="Activos"
        inactive-label="Inactivos"
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
      empty-message="No hay conjuntos de opciones registrados."
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

    <ResultOptionSetFormModal v-model:open="modal.open" :entity="modal.entity" @saved="reload" />
  </div>
</template>
