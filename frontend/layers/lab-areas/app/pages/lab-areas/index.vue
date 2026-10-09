<script setup lang="ts">
import type { UiDataTableColumn } from '~/components/ui/UiDataTable.vue'
import type { LabAreaRead } from '../../types/lab-areas'

definePageMeta({ layout: 'default' })

const labAreasApi = useLabAreas()
const activeFilter = ref<boolean | undefined>(undefined)

const search = ref('')

const { rows, total, page, pageSize, loading, loadError, searchTerm, reload } = usePaginatedList(
  params => labAreasApi.list({ ...params, active: activeFilter.value }),
  { resource: '/lab-areas', search, filters: [activeFilter], errorMessage: 'No se pudieron cargar las áreas.' }
)

const modal = useEntityModal<LabAreaRead>()

const columns: UiDataTableColumn<LabAreaRead>[] = [
  { key: 'code', label: 'Código' },
  { key: 'name', label: 'Nombre' },
  { key: 'current_manager', label: 'Encargado' },
  { key: 'is_active', label: 'Estado' },
  { key: 'id', label: '', class: 'text-right' }
]
</script>

<template>
  <div class="space-y-6">
    <UiPageHeader
      title="Áreas"
      description="Gestión de las áreas del laboratorio y su encargado."
      action-label="Nueva"
      @action="modal.openCreate()"
    />

    <UiListToolbar
      v-model:search="search"
      search-placeholder="Buscar por código o nombre…"
      :searching="loading"
    >
      <UiActiveFilter
        id="lab-area-active-filter"
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
      empty-message="No hay áreas registradas."
      :search-term="searchTerm"
      @update:page="page = $event"
      @clear-search="search = ''"
    >
      <template #cell-current_manager="{ row }">
        <span v-if="row.current_manager" class="text-text">
          {{ row.current_manager.staff_name }}
        </span>
        <span v-else class="text-text-muted">
          Sin encargado
        </span>
      </template>
      <template #cell-is_active="{ value }">
        <UiStatusBadge :active="value as boolean" />
      </template>
      <template #cell-id="{ row }">
        <UiButton variant="ghost" size="sm" @click="modal.openEdit(row)">
          Ver / Editar
        </UiButton>
      </template>
    </UiDataTable>

    <LabAreaFormModal v-model:open="modal.open" :entity="modal.entity" @saved="reload" />
  </div>
</template>
