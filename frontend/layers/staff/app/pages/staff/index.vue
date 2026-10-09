<script setup lang="ts">
import type { UiDataTableColumn } from '~/components/ui/UiDataTable.vue'
import type { StaffRead } from '../../types/staff'

definePageMeta({ layout: 'default' })

const staffApi = useStaff()
const activeFilter = ref<boolean | undefined>(undefined)

const search = ref('')

const { rows, total, page, pageSize, loading, loadError, searchTerm, reload } = usePaginatedList(
  params => staffApi.list({ ...params, active: activeFilter.value }),
  { resource: '/staff', search, filters: [activeFilter], errorMessage: 'No se pudo cargar el personal.' }
)

const modal = useEntityModal<StaffRead>()

const columns: UiDataTableColumn<StaffRead>[] = [
  { key: 'document_number', label: 'Documento' },
  { key: 'first_name', label: 'Nombres' },
  { key: 'last_name', label: 'Apellidos' },
  { key: 'job_title', label: 'Cargo' },
  { key: 'is_active', label: 'Estado' },
  { key: 'id', label: '', class: 'text-right' }
]
</script>

<template>
  <div class="space-y-6">
    <UiPageHeader
      title="Personal"
      description="Gestión del personal del laboratorio."
      action-label="Nuevo"
      @action="modal.openCreate()"
    />

    <UiListToolbar
      v-model:search="search"
      search-placeholder="Buscar por nombre, documento, email o cargo…"
      :searching="loading"
    >
      <UiActiveFilter id="staff-active-filter" v-model="activeFilter" />
    </UiListToolbar>

    <UiAlert v-if="loadError" :message="loadError" />

    <UiDataTable
      :columns="columns"
      :rows="rows"
      :loading="loading"
      :page="page"
      :page-size="pageSize"
      :total="total"
      empty-message="No hay personal registrado."
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

    <StaffFormModal v-model:open="modal.open" :entity="modal.entity" @saved="reload" />
  </div>
</template>
