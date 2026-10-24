<script setup lang="ts">
import type { UiDataTableColumn } from '#andromeda/components/ui/UiDataTable.vue'
import type { UiSelectOption } from '#andromeda/components/ui/UiSelect.vue'
import type { LabTestCatalogOption, LabTestRead } from '../../types/lab-tests'

definePageMeta({ layout: 'default', leo: { tag: LAB_TESTS_TAGS.view } })

const createTag = LAB_TESTS_TAGS.create

// Quien solo consulta ve "Ver"; con algún permiso de cambio, "Ver / Editar".
const canModify = useCan([
  LAB_TESTS_TAGS.edit, LAB_TESTS_TAGS.changeStatus, LAB_TESTS_TAGS.setPreconditions,
  LAB_TESTS_TAGS.setSampleTypes, LAB_TESTS_TAGS.setConsentDocuments
], 'any')
// El filtro y la columna de área vienen del catálogo de áreas: exige su `view`.
const canConsultAreas = useCan(MODULE_VIEW.labAreas.tag)

const labTestsApi = useLabTests()
const activeFilter = ref<boolean | undefined>(undefined)
const areaFilter = ref('')

const search = ref('')

const { rows, total, page, pageSize, loading, loadError, searchTerm, reload } = usePaginatedList({
  fetchPage: (params, { signal }) => labTestsApi.list({ ...params, active: activeFilter.value, area_id: areaFilter.value || undefined }, { signal }),
  search,
  filters: [activeFilter, areaFilter],
  errorMessage: 'No se pudieron cargar los exámenes.',
  mapError: leoErrorMessage,
  urlSync: useRouteQuerySync(),
  cache: listCache('/lab-tests')
})

const modal = useEntityModal<LabTestRead>()

const areas = ref<LabTestCatalogOption[]>([])
const areaOptions = computed<UiSelectOption[]>(() =>
  areas.value.map(area => ({ value: area.id, label: `${area.name} (${area.code})` }))
)
const areaName = (areaId: string) => areas.value.find(area => area.id === areaId)?.name ?? '—'

onMounted(async () => {
  if (!canConsultAreas.value) return
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
    >
      <template #actions>
        <LeoCan :tag="createTag">
          <UiButton variant="primary" @click="modal.openCreate()">
            Nuevo examen
          </UiButton>
        </LeoCan>
      </template>
    </UiPageHeader>

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
      <UiFormField
        v-if="canConsultAreas"
        label="Área"
        field-id="lab-test-area-filter"
        class="w-64"
      >
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
          {{ canModify ? 'Ver / Editar' : 'Ver' }}
        </UiButton>
      </template>
    </UiDataTable>

    <LabTestFormModal v-model:open="modal.open" :entity="modal.entity" @saved="reload" />
  </div>
</template>
