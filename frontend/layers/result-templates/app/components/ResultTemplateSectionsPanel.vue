<script setup lang="ts">
import type { ResultTemplateVersionContent } from '../composables/useResultTemplateVersionContent'
import type { ResultTemplateSectionRead } from '../types/result-templates'

/**
 * Secciones de una versión de plantilla: lista, crear/editar en modal y
 * desactivar/reactivar con motivo (nada se elimina; solo en borrador). Las
 * inactivas se ven con "Mostrar inactivas".
 */
const props = defineProps<{
  content: ResultTemplateVersionContent
  editable: boolean
}>()

const modal = useEntityModal<ResultTemplateSectionRead>()
const showInactive = ref(false)

const visibleSections = computed(() =>
  showInactive.value ? props.content.sections : props.content.sections.filter(section => section.is_active)
)

const nextSortOrder = computed(() =>
  props.content.sections.reduce((max, section) => Math.max(max, section.sort_order + 1), 0)
)

const toggle = useToggleActive(
  async (section: ResultTemplateSectionRead, change) => {
    await useResultTemplates().updateSection(props.content.templateId, props.content.versionId, section.id, change)
    await Promise.all([props.content.loadSections(), props.content.loadAnalytes()])
  },
  { errorMessage: 'No se pudo cambiar el estado de la sección.', mapError: leoErrorMessage }
)
</script>

<template>
  <UiSection title="Secciones" description="Agrupan los analitos en el reporte." divided>
    <template #actions>
      <UiCheckbox v-model="showInactive" label="Mostrar inactivas" />
      <UiButton v-if="editable" variant="secondary" size="sm" @click="modal.openCreate()">
        Agregar sección
      </UiButton>
    </template>

    <UiAlert v-if="content.sectionsError" :message="content.sectionsError" />
    <UiItemList
      :items="visibleSections"
      :row-key="(section: ResultTemplateSectionRead) => section.id"
      :loading="content.sectionsLoading"
      :inactive="(section: ResultTemplateSectionRead) => !section.is_active"
      empty-message="Sin secciones todavía."
    >
      <template #default="{ item }">
        <span class="text-text">{{ item.name }}</span>
        <span class="text-text-muted"> (orden {{ item.sort_order }})</span>
      </template>
      <template #trailing="{ item }">
        <UiStatusBadge v-if="!item.is_active" :active="false" label="Inactiva" />
        <template v-if="editable">
          <UiButton variant="ghost" size="sm" @click="modal.openEdit(item)">
            Editar
          </UiButton>
          <UiButton :variant="item.is_active ? 'danger-ghost' : 'ghost'" size="sm" @click="toggle.ask(item)">
            {{ item.is_active ? 'Desactivar' : 'Reactivar' }}
          </UiButton>
        </template>
      </template>
    </UiItemList>

    <ResultTemplateSectionFormModal
      v-model:open="modal.open"
      :entity="modal.entity"
      :template-id="content.templateId"
      :version-id="content.versionId"
      :next-sort-order="nextSortOrder"
      @saved="content.loadSections()"
    />

    <UiToggleActiveModal
      :state="toggle"
      noun="la sección"
      :name="toggle.target?.name"
      deactivate-hint="Para publicar, los analitos que la usen deben pasar a otra sección."
    />
  </UiSection>
</template>
