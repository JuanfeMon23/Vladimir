<script setup lang="ts">
import type { UiDataTableColumn } from '#andromeda/components/ui/UiDataTable.vue'
import type { CatalogItem, CatalogSlug } from '~/types/catalogs'
import { CATALOG_DEFINITIONS, catalogDefinition } from '../../utils/catalogDefinitions'

type CatalogRow = CatalogItem & Record<string, unknown>

definePageMeta({ layout: 'default', leo: { tag: CATALOGS_TAGS.view } })

/**
 * Gestión de los catálogos de categoría (`/catalogs/{slug}`): una vista con
 * selector de catálogo, listado con las columnas de comportamiento de cada uno,
 * y crear / editar / activar y desactivar en modal (nada se elimina). El
 * catálogo elegido vive en `?catalog=`.
 */
const route = useRoute()
const router = useRouter()
const catalogApi = useCatalogApi()

const catalogOptions = CATALOG_DEFINITIONS.map(definition => ({ value: definition.slug, label: definition.label }))
const slug = computed<CatalogSlug>(() =>
  catalogDefinition(typeof route.query.catalog === 'string' ? route.query.catalog : null).slug
)
const selectedCatalog = computed({
  get: () => slug.value,
  set: (value: string) => { void router.replace({ query: { ...route.query, catalog: value } }) }
})
const definition = computed(() => catalogDefinition(slug.value))

const activeFilter = ref<boolean | undefined>(undefined)
const items = ref<CatalogRow[]>([])
const loading = ref(false)
const loadError = ref<string | null>(null)

const rows = computed(() =>
  activeFilter.value === undefined ? items.value : items.value.filter(row => row.is_active === activeFilter.value)
)
const nextSortOrder = computed(() => items.value.reduce((max, row) => Math.max(max, row.sort_order + 1), 0))

let requestId = 0
async function reload() {
  const current = ++requestId
  loading.value = true
  loadError.value = null
  try {
    const result = await catalogApi.list(slug.value, { includeInactive: true }) as CatalogRow[]
    if (current === requestId) items.value = result
  } catch (err) {
    if (current === requestId) {
      items.value = []
      loadError.value = leoErrorMessage(err)
    }
  } finally {
    if (current === requestId) loading.value = false
  }
}
watch(slug, () => {
  items.value = []
  void reload()
}, { immediate: true })

const modal = useEntityModal<CatalogRow>()
const canModify = useCan([CATALOGS_TAGS.edit, CATALOGS_TAGS.changeStatus], 'any')

const columns = computed<UiDataTableColumn<CatalogRow>[]>(() => [
  { key: 'code', label: 'Código' },
  { key: 'name', label: 'Nombre' },
  { key: 'sort_order', label: 'Orden' },
  ...definition.value.extraFields.map(field => ({ key: field.key, label: field.label })),
  { key: 'is_active', label: 'Estado' },
  { key: 'id', label: '', class: 'text-right' }
])
</script>

<template>
  <div class="space-y-6">
    <UiPageHeader
      title="Catálogos"
      description="Listas de categoría que usan los módulos: sus etiquetas y comportamiento salen de aquí, no del código."
    >
      <template #actions>
        <LeoCan :tag="CATALOGS_TAGS.create">
          <UiButton variant="primary" @click="modal.openCreate()">
            {{ definition.newLabel }}
          </UiButton>
        </LeoCan>
      </template>
    </UiPageHeader>

    <div class="flex flex-wrap items-end gap-4">
      <UiFormField label="Catálogo" field-id="catalog-select" class="w-full sm:w-72">
        <UiSelect v-model="selectedCatalog" :options="catalogOptions" />
      </UiFormField>
      <UiActiveFilter id="catalog-active-filter" v-model="activeFilter" />
    </div>
    <p class="text-sm text-text-muted">
      {{ definition.description }}
    </p>

    <UiAlert v-if="loadError" :message="loadError" />

    <UiDataTable
      :columns="columns"
      :rows="rows"
      :loading="loading"
      empty-message="No hay valores en este catálogo."
    >
      <template #cell-code="{ value }">
        <span class="font-mono">{{ value }}</span>
      </template>
      <template v-for="field in definition.extraFields.filter(extra => extra.kind === 'boolean')" :key="field.key" #[`cell-${field.key}`]="{ value }">
        <UiStatusBadge :variant="value ? 'primary' : 'neutral'" :label="value ? 'Sí' : 'No'" />
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

    <CatalogFormModal
      :key="slug"
      v-model:open="modal.open"
      :slug="slug"
      :entity="modal.entity"
      :next-sort-order="nextSortOrder"
      @saved="reload"
    />
  </div>
</template>
