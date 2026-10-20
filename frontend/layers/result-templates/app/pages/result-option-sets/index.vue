<script setup lang="ts">
import type { UiDataTableColumn } from '~/components/ui/UiDataTable.vue'
import type { ResultOptionSetRead } from '../../types/result-templates'

definePageMeta({ layout: 'default', leo: { tag: RESULT_TEMPLATES_TAGS.view } })

const manageTag = RESULT_TEMPLATES_TAGS.manageOptionSets
const canManage = useCan(manageTag)

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
    >
      <template #actions>
        <LeoCan :tag="manageTag">
          <UiButton variant="primary" @click="modal.openCreate()">
            Nuevo conjunto
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
          {{ canManage ? 'Ver / Editar' : 'Ver' }}
        </UiButton>
      </template>
    </UiDataTable>

    <ResultOptionSetFormModal v-model:open="modal.open" :entity="modal.entity" @saved="reload" />
  </div>
</template>
