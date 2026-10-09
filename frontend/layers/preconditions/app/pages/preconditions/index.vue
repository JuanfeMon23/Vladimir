<script setup lang="ts">
import { preconditionCategoryLabel } from '../../types/preconditions'
import type { PreconditionRead } from '../../types/preconditions'

definePageMeta({ layout: 'default' })

const preconditionsApi = usePreconditions()
const activeFilter = ref<boolean | undefined>(undefined)

const search = ref('')

const { rows, total, page, pageSize, loading, loadError, searchTerm, reload } = usePaginatedList(
  params => preconditionsApi.list({ ...params, active: activeFilter.value }),
  { resource: '/preconditions', search, filters: [activeFilter], errorMessage: 'No se pudieron cargar las precondiciones.' }
)

const modal = useEntityModal<PreconditionRead>()
</script>

<template>
  <div class="space-y-6">
    <UiPageHeader
      title="Precondiciones"
      description="Precondiciones de examen y sus ítems (condiciones específicas)."
      action-label="Nueva precondición"
      @action="modal.openCreate()"
    />

    <UiListToolbar
      v-model:search="search"
      search-placeholder="Buscar por código o nombre…"
      :searching="loading"
    >
      <UiActiveFilter
        id="precondition-active-filter"
        v-model="activeFilter"
        active-label="Activas"
        inactive-label="Inactivas"
      />
    </UiListToolbar>

    <UiAlert v-if="loadError" :message="loadError" />

    <UiExpandableList
      :items="rows"
      :row-key="(root: PreconditionRead) => root.id"
      :loading="loading"
      empty-message="No hay precondiciones registradas."
      :page="page"
      :page-size="pageSize"
      :total="total"
      :search-term="searchTerm"
      @update:page="page = $event"
      @clear-search="search = ''"
    >
      <template #header="{ item: root }">
        <div>
          <p class="font-medium text-text">
            {{ root.name }}
            <span class="font-normal text-text-muted">({{ root.code }})</span>
          </p>
          <p class="text-xs text-text-muted">
            {{ preconditionCategoryLabel(root.category) }}
          </p>
        </div>
      </template>

      <template #summary="{ item: root }">
        <div class="flex items-center gap-3">
          <span class="text-xs text-text-muted">
            {{ root.items?.length ?? 0 }} ítem(s)
          </span>
          <UiStatusBadge :active="root.is_active" />
        </div>
      </template>

      <template #content="{ item: root }">
        <div class="flex items-center justify-between">
          <h4 class="text-xs font-semibold uppercase tracking-wide text-text-muted">
            Ítems
          </h4>
          <UiButton variant="ghost" size="sm" @click="modal.openEdit(root)">
            Ver / Editar
          </UiButton>
        </div>

        <UiItemList
          :items="root.items ?? []"
          :row-key="(item: PreconditionRead) => item.id"
          empty-message="Sin ítems."
        >
          <template #default="{ item }">
            <span class="text-text">{{ item.name }}</span>
            <span class="text-text-muted"> ({{ item.code }})</span>
          </template>
          <template #trailing="{ item }">
            <UiStatusBadge :active="item.is_active" />
            <UiButton variant="ghost" size="sm" @click="modal.openEdit(item)">
              Editar
            </UiButton>
          </template>
        </UiItemList>
      </template>
    </UiExpandableList>

    <PreconditionFormModal v-model:open="modal.open" :entity="modal.entity" @saved="reload" />
  </div>
</template>
