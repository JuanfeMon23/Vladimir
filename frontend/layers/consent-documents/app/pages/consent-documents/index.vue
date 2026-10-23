<script setup lang="ts">
import type { UiDataTableColumn } from '#andromeda/components/ui/UiDataTable.vue'
import { CONSENT_DOCUMENT_TYPE_LABELS } from '../../types/consent-documents'
import type { ConsentDocumentRead } from '../../types/consent-documents'
import { isGeneralConsent } from '../../utils/consentDocuments'

definePageMeta({ layout: 'default', leo: { tag: CONSENT_DOCUMENTS_TAGS.view } })

const createTag = CONSENT_DOCUMENTS_TAGS.create

// Quien solo consulta ve "Ver"; con algún permiso de cambio, "Ver / Editar".
const canModify = useCan([CONSENT_DOCUMENTS_TAGS.edit, CONSENT_DOCUMENTS_TAGS.changeStatus, CONSENT_DOCUMENTS_TAGS.createVersion, CONSENT_DOCUMENTS_TAGS.editVersion, CONSENT_DOCUMENTS_TAGS.publishVersion, CONSENT_DOCUMENTS_TAGS.retireVersion], 'any')

const consentDocumentsApi = useConsentDocuments()
const activeFilter = ref<boolean | undefined>(undefined)

const search = ref('')

const { rows, total, page, pageSize, loading, loadError, searchTerm, reload } = usePaginatedList({
  fetchPage: (params, { signal }) => consentDocumentsApi.list({ ...params, active: activeFilter.value }, { signal }),
  search,
  filters: [activeFilter],
  errorMessage: 'No se pudieron cargar los documentos.',
  mapError: leoErrorMessage,
  urlSync: useRouteQuerySync(),
  cache: listCache('/consent-documents')
})

const modal = useEntityModal<ConsentDocumentRead>()
useOpenEntityFromQuery(modal, consentDocumentsApi.get)

const columns: UiDataTableColumn<ConsentDocumentRead>[] = [
  { key: 'code', label: 'Código' },
  { key: 'name', label: 'Nombre' },
  { key: 'document_type', label: 'Tipo' },
  { key: 'is_active', label: 'Estado' },
  { key: 'id', label: '', class: 'text-right' }
]
</script>

<template>
  <div class="space-y-6">
    <UiPageHeader
      title="Documentos a firmar"
      description="Gestión de documentos de consentimiento y sus versiones (cada versión lleva su PDF). El consentimiento general se firma antes de cualquier examen."
    >
      <template #actions>
        <LeoCan :tag="createTag">
          <UiButton variant="primary" @click="modal.openCreate()">
            Nuevo documento
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
        id="consent-document-active-filter"
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
      empty-message="No hay documentos registrados."
      :search-term="searchTerm"
      @update:page="page = $event"
      @clear-search="search = ''"
    >
      <template #cell-document_type="{ row }">
        <span class="inline-flex flex-wrap items-center gap-2">
          {{ CONSENT_DOCUMENT_TYPE_LABELS[row.document_type] ?? row.document_type }}
          <UiStatusBadge v-if="row.is_active && isGeneralConsent(row)" variant="primary" label="General vigente" dot />
        </span>
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

    <ConsentDocumentFormModal v-model:open="modal.open" :entity="modal.entity" @saved="reload" />
  </div>
</template>
