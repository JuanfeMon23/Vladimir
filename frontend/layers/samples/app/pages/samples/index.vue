<script setup lang="ts">
import type { SampleRead, SampleTypeRead } from '../../types/samples'

definePageMeta({ layout: 'default', leo: { tag: SAMPLES_TAGS.view } })

const createTag = SAMPLES_TAGS.create

// Quien solo consulta ve "Ver"; con algún permiso de cambio, "Ver / Editar".
const canModify = useCan([SAMPLES_TAGS.edit, SAMPLES_TAGS.changeStatus, SAMPLES_TAGS.addType], 'any')

const samplesApi = useSamples()
const activeFilter = ref<boolean | undefined>(undefined)

const search = ref('')

const { rows, total, page, pageSize, loading, loadError, searchTerm, reload } = usePaginatedList({
  fetchPage: (params, { signal }) => samplesApi.list({ ...params, active: activeFilter.value }, { signal }),
  search,
  filters: [activeFilter],
  errorMessage: 'No se pudieron cargar las muestras.',
  mapError: leoErrorMessage,
  urlSync: useRouteQuerySync(),
  cache: listCache('/samples')
})

const modal = useEntityModal<SampleRead>()
</script>

<template>
  <div class="space-y-6">
    <UiPageHeader
      title="Muestras"
      description="Muestras (contenedores) y sus tipos (tubo/tapa, aditivo, volumen)."
    >
      <template #actions>
        <LeoCan :tag="createTag">
          <UiButton variant="primary" @click="modal.openCreate()">
            Nueva muestra
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
        id="sample-active-filter"
        v-model="activeFilter"
        active-label="Activas"
        inactive-label="Inactivas"
      />
    </UiListToolbar>

    <UiAlert v-if="loadError" :message="loadError" />

    <UiExpandableList
      :items="rows"
      :row-key="(sample: SampleRead) => sample.id"
      :loading="loading"
      empty-message="No hay muestras registradas."
      :page="page"
      :page-size="pageSize"
      :total="total"
      :search-term="searchTerm"
      @update:page="page = $event"
      @clear-search="search = ''"
    >
      <template #header="{ item: sample }">
        <div>
          <p class="font-medium text-text">
            {{ sample.name }}
            <span class="font-normal text-text-muted">({{ sample.code }})</span>
          </p>
          <p v-if="sample.description" class="text-xs text-text-muted">
            {{ sample.description }}
          </p>
        </div>
      </template>

      <template #summary="{ item: sample }">
        <div class="flex items-center gap-3">
          <span class="text-xs text-text-muted">
            {{ sample.types.length }} tipo(s)
          </span>
          <UiStatusBadge :active="sample.is_active" />
        </div>
      </template>

      <template #content="{ item: sample }">
        <div class="flex items-center justify-between">
          <h4 class="text-xs font-semibold uppercase tracking-wide text-text-muted">
            Tipos de muestra
          </h4>
          <UiButton variant="ghost" size="sm" @click="modal.openEdit(sample)">
            {{ canModify ? 'Ver / Editar' : 'Ver' }}
          </UiButton>
        </div>

        <UiItemList
          :items="sample.types"
          :row-key="(type: SampleTypeRead) => type.id"
          empty-message="Sin tipos."
        >
          <template #default="{ item }">
            <SampleTypeCapChip :label="`${item.name} (${item.code})`" :cap-color-hex="item.cap_color_hex" />
          </template>
          <template #trailing="{ item }">
            <UiStatusBadge :active="item.is_active" />
          </template>
        </UiItemList>
      </template>
    </UiExpandableList>

    <SampleFormModal v-model:open="modal.open" :entity="modal.entity" @saved="reload" />
  </div>
</template>
