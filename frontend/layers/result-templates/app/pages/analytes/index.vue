<script setup lang="ts">
import type { UiDataTableColumn } from '~/components/ui/UiDataTable.vue'
import type { AnalyteRead } from '../../types/result-templates'

definePageMeta({ layout: 'default', leo: { tag: RESULT_TEMPLATES_TAGS.view } })

const manageTag = RESULT_TEMPLATES_TAGS.manageAnalytes
const canManage = useCan(manageTag)

const analytesApi = useAnalytes()
const activeFilter = ref<boolean | undefined>(undefined)

const search = ref('')

const { rows, total, page, pageSize, loading, loadError, searchTerm, reload } = usePaginatedList(
  params => analytesApi.list({ ...params, active: activeFilter.value }),
  { resource: '/analytes', search, filters: [activeFilter], errorMessage: 'No se pudieron cargar los analitos.' }
)

const modal = useEntityModal<AnalyteRead>()

const columns: UiDataTableColumn<AnalyteRead>[] = [
  { key: 'code', label: 'Código' },
  { key: 'name', label: 'Nombre' },
  { key: 'default_unit', label: 'Unidad' },
  { key: 'is_active', label: 'Estado' },
  { key: 'id', label: '', class: 'text-right' }
]
</script>

<template>
  <div class="space-y-6">
    <UiPageHeader
      title="Analitos"
      description="Catálogo de analitos disponibles para plantillas de resultados."
    >
      <template #actions>
        <LeoCan :tag="manageTag">
          <UiButton variant="primary" @click="modal.openCreate()">
            Nuevo analito
          </UiButton>
        </LeoCan>
      </template>
    </UiPageHeader>

    <UiListToolbar
      v-model:search="search"
      search-placeholder="Buscar por código, nombre o LOINC…"
      :searching="loading"
    >
      <UiActiveFilter
        id="analyte-active-filter"
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
      empty-message="No hay analitos registrados."
      :search-term="searchTerm"
      @update:page="page = $event"
      @clear-search="search = ''"
    >
      <template #cell-default_unit="{ value }">
        <span :class="value ? 'text-text' : 'text-text-muted'">{{ value || '—' }}</span>
      </template>
      <template #cell-is_active="{ value }">
        <UiStatusBadge :active="value as boolean" />
      </template>
      <template #cell-id="{ row }">
        <UiButton variant="ghost" size="sm" @click="modal.openEdit(row)">
          {{ canManage ? 'Ver / Editar' : 'Ver' }}
        </UiButton>
      </template>
    </UiDataTable>

    <AnalyteFormModal v-model:open="modal.open" :entity="modal.entity" @saved="reload" />
  </div>
</template>
