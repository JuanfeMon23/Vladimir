<script setup lang="ts">
import type { UiDataTableColumn } from '#andromeda/components/ui/UiDataTable.vue'
import type { UnitRead } from '../../types/result-templates'

definePageMeta({ layout: 'default', leo: { tag: RESULT_TEMPLATES_TAGS.view } })

const manageTag = RESULT_TEMPLATES_TAGS.manageUnits
const canManage = useCan(manageTag)

const unitsApi = useUnits()
const activeFilter = ref<boolean | undefined>(undefined)

const search = ref('')

const { rows, total, page, pageSize, loading, loadError, searchTerm, reload } = usePaginatedList({
  fetchPage: (params, { signal }) => unitsApi.list({ ...params, active: activeFilter.value }, { signal }),
  search,
  filters: [activeFilter],
  errorMessage: 'No se pudieron cargar las unidades.',
  mapError: leoErrorMessage,
  urlSync: useRouteQuerySync(),
  cache: listCache('/units')
})

const modal = useEntityModal<UnitRead>()

const columns: UiDataTableColumn<UnitRead>[] = [
  { key: 'code', label: 'Código UCUM' },
  { key: 'symbol', label: 'Símbolo' },
  { key: 'name', label: 'Nombre' },
  { key: 'is_active', label: 'Estado' },
  { key: 'id', label: '', class: 'text-right' }
]
</script>

<template>
  <div class="space-y-6">
    <UiPageHeader
      title="Unidades de medida"
      description="Catálogo UCUM de unidades para analitos y plantillas de resultados."
    >
      <template #actions>
        <LeoCan :tag="manageTag">
          <UiButton variant="primary" @click="modal.openCreate()">
            Nueva unidad
          </UiButton>
        </LeoCan>
      </template>
    </UiPageHeader>

    <UiListToolbar
      v-model:search="search"
      search-placeholder="Buscar por código, símbolo o nombre…"
      :searching="loading"
    >
      <UiActiveFilter
        id="unit-active-filter"
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
      empty-message="No hay unidades registradas."
      :search-term="searchTerm"
      @update:page="page = $event"
      @clear-search="search = ''"
    >
      <template #cell-code="{ value }">
        <span class="font-mono">{{ value }}</span>
      </template>
      <template #cell-is_active="{ value }">
        <UiStatusBadge :active="value as boolean" :label="value ? 'Activa' : 'Inactiva'" />
      </template>
      <template #cell-id="{ row }">
        <UiButton variant="ghost" size="sm" @click="modal.openEdit(row)">
          {{ canManage ? 'Ver / Editar' : 'Ver' }}
        </UiButton>
      </template>
    </UiDataTable>

    <UnitFormModal v-model:open="modal.open" :entity="modal.entity" @saved="reload" />
  </div>
</template>
