<script setup lang="ts">
import type { UiDataTableColumn } from '#andromeda/components/ui/UiDataTable.vue'
import type { UiSelectOption } from '#andromeda/components/ui/UiSelect.vue'
import type { LabTestCatalogOption, LabTestRead } from '../../types/lab-tests'

definePageMeta({ layout: 'default' })

const labTestsApi = useLabTests()
const activeFilter = ref<boolean | undefined>(undefined)
const areaFilter = ref('')

const search = ref('')

const { rows, total, page, pageSize, loading, loadError, searchTerm, reload } = usePaginatedList(
  params => labTestsApi.list({ ...params, active: activeFilter.value, area_id: areaFilter.value || undefined }),
  { resource: '/lab-tests', search, filters: [activeFilter, areaFilter], errorMessage: 'No se pudieron cargar los exámenes.' }
)

const modal = useEntityModal<LabTestRead>()

const areas = ref<LabTestCatalogOption[]>([])
const areaOptions = computed<UiSelectOption[]>(() =>
  areas.value.map(area => ({ value: area.id, label: `${area.name} (${area.code})` }))
)
const areaName = (areaId: string) => areas.value.find(area => area.id === areaId)?.name ?? '—'

onMounted(async () => {
  try {
    areas.value = await labTestsApi.listAreaOptions()
  } catch {
    // El filtro y la columna de área son un extra; el listado funciona sin ellos.
  }
})

const columns: UiDataTableColumn<LabTestRead>[] = [
  { key: 'code', label: 'Código' },
  { key: 'name', label: 'Nombre' },
  { key: 'area_id', label: 'Área' },
  { key: 'is_active', label: 'Estado' },
  { key: 'id', label: '', class: 'text-right' }
]
</script>

<template>
  <div class="space-y-6">
    <UiPageHeader
      title="Exámenes"
      description="Catálogo de exámenes de laboratorio y su configuración."
      action-label="Nuevo examen"
      @action="modal.openCreate()"
    />

    <UiListToolbar
      v-model:search="search"
      search-placeholder="Buscar por código, nombre, CUPS o LOINC…"
      :searching="loading"
    >
      <UiActiveFilter
        id="lab-test-active-filter"
        v-model="activeFilter"
        active-label="Activos"
        inactive-label="Inactivos"
      />
      <UiFormField label="Área" field-id="lab-test-area-filter" class="w-64">
        <UiSelect v-model="areaFilter" :options="areaOptions" empty-label="Todas" />
      </UiFormField>
    </UiListToolbar>

    <UiAlert v-if="loadError" :message="loadError" />

    <UiDataTable
      :columns="columns"
      :rows="rows"
      :loading="loading"
      :page="page"
      :page-size="pageSize"
      :total="total"
      empty-message="No hay exámenes registrados."
      :search-term="searchTerm"
      @update:page="page = $event"
      @clear-search="search = ''"
    >
      <template #cell-area_id="{ value }">
        {{ areaName(value as string) }}
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

    <LabTestFormModal v-model:open="modal.open" :entity="modal.entity" @saved="reload" />
  </div>
</template>
