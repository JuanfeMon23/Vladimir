<script setup lang="ts">
import type { UiDataTableColumn } from '~/components/ui/UiDataTable.vue'
import type { ResultTemplateRead } from '../../types/result-templates'

definePageMeta({ layout: 'default' })

const resultTemplatesApi = useResultTemplates()
const activeFilter = ref<boolean | undefined>(undefined)

const search = ref('')

const { rows, total, page, pageSize, loading, loadError, searchTerm, reload } = usePaginatedList(
  params => resultTemplatesApi.list({ ...params, active: activeFilter.value }),
  { resource: '/result-templates', search, filters: [activeFilter], errorMessage: 'No se pudieron cargar las plantillas.' }
)

const modal = useEntityModal<ResultTemplateRead>()
useOpenEntityFromQuery(modal, resultTemplatesApi.get)

const columns: UiDataTableColumn<ResultTemplateRead>[] = [
  { key: 'code', label: 'Código' },
  { key: 'name', label: 'Nombre' },
  { key: 'is_active', label: 'Estado' },
  { key: 'id', label: '', class: 'text-right' }
]
</script>

<template>
  <div class="space-y-6">
    <UiPageHeader
      title="Plantillas de resultados"
      description="Gestión de plantillas de resultados y sus versiones."
      action-label="Nueva plantilla"
      @action="modal.openCreate()"
    />

    <UiListToolbar
      v-model:search="search"
      search-placeholder="Buscar por código o nombre…"
      :searching="loading"
    >
      <UiActiveFilter
        id="result-template-active-filter"
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
      empty-message="No hay plantillas registradas."
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

    <ResultTemplateFormModal v-model:open="modal.open" :entity="modal.entity" @saved="reload" />
  </div>
</template>
