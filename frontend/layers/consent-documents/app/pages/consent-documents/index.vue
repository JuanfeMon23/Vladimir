<script setup lang="ts">
import type { UiDataTableColumn } from '~/components/ui/UiDataTable.vue'
import { CONSENT_DOCUMENT_TYPE_LABELS } from '../../types/consent-documents'
import type { ConsentDocumentRead } from '../../types/consent-documents'
import { isGeneralConsent } from '../../utils/consentDocuments'

definePageMeta({ layout: 'default' })

const consentDocumentsApi = useConsentDocuments()
const activeFilter = ref<boolean | undefined>(undefined)

const search = ref('')

const { rows, total, page, pageSize, loading, loadError, searchTerm, reload } = usePaginatedList(
  params => consentDocumentsApi.list({ ...params, active: activeFilter.value }),
  { resource: '/consent-documents', search, filters: [activeFilter], errorMessage: 'No se pudieron cargar los documentos.' }
)

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
      action-label="Nuevo documento"
      @action="modal.openCreate()"
    />

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
          Ver / Editar
        </UiButton>
      </template>
    </UiDataTable>

    <ConsentDocumentFormModal v-model:open="modal.open" :entity="modal.entity" @saved="reload" />
  </div>
</template>
