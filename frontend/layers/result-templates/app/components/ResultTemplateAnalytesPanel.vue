<script setup lang="ts">
import type { ResultTemplateVersionContent } from '../composables/useResultTemplateVersionContent'
import { RESULT_TYPES_WITH_OPTION_SET, RESULT_TYPE_LABELS } from '../types/result-templates'
import type { ResultTemplateAnalyteRead } from '../types/result-templates'

/**
 * Analitos de una versión de plantilla, agrupados por sección: agregar /
 * editar en modal, desactivar/reactivar con motivo (nada se elimina) y, al
 * expandir cada uno, sus rangos de referencia
 * (`ResultTemplateReferenceRanges`). Los inactivos, con "Mostrar inactivos".
 */
const props = defineProps<{
  content: ResultTemplateVersionContent
  editable: boolean
}>()

const modal = useEntityModal<ResultTemplateAnalyteRead>()
const showInactive = ref(false)

const visibleAnalytes = computed(() =>
  showInactive.value ? props.content.templateAnalytes : props.content.templateAnalytes.filter(item => item.is_active)
)

const groups = computed(() => {
  const bySection = new Map<string, ResultTemplateAnalyteRead[]>()
  for (const item of visibleAnalytes.value) {
    const key = item.section_id ?? ''
    bySection.set(key, [...(bySection.get(key) ?? []), item])
  }
  // Orden de las secciones; "Sin sección" al final.
  const order = [...props.content.sections.map(section => section.id), '']
  return [...bySection.entries()]
    .sort(([a], [b]) => order.indexOf(a) - order.indexOf(b))
    .map(([sectionId, items]) => ({ sectionId: sectionId || null, items }))
})

const toggle = useToggleActive(
  async (item: ResultTemplateAnalyteRead, change) => {
    await useResultTemplates().updateTemplateAnalyte(props.content.templateId, props.content.versionId, item.id, change)
    await props.content.loadAnalytes()
  },
  { errorMessage: 'No se pudo cambiar el estado del analito.' }
)

function unitText(item: ResultTemplateAnalyteRead) {
  return item.unit || (item.unit_id ? props.content.unitName(item.unit_id) : '—')
}

function detail(item: ResultTemplateAnalyteRead) {
  if (item.result_type === 'numeric') return `Unidad: ${unitText(item)} · Decimales: ${item.decimals ?? '—'}`
  if (RESULT_TYPES_WITH_OPTION_SET.includes(item.result_type)) return `Conjunto: ${props.content.optionSetName(item.option_set_id)}`
  if (item.result_type === 'calculated') return `Fórmula: ${item.formula || '—'} · Unidad: ${unitText(item)}`
  return `Valor por defecto: ${item.default_value || '—'}`
}
</script>

<template>
  <UiSection title="Analitos de la plantilla" description="Expande un analito para ver y editar sus rangos de referencia." divided>
    <template #actions>
      <UiCheckbox v-model="showInactive" label="Mostrar inactivos" />
      <UiButton v-if="editable" variant="secondary" size="sm" @click="modal.openCreate()">
        Agregar analito
      </UiButton>
    </template>

    <UiAlert v-if="content.analytesError" :message="content.analytesError" />

    <div v-if="content.analytesLoading" class="flex items-center gap-2 text-sm text-text-muted">
      <UiSpinner size="sm" color="primary" />
      <span>Cargando analitos…</span>
    </div>

    <p
      v-else-if="visibleAnalytes.length === 0"
      class="rounded-lg border border-dashed border-border px-4 py-4 text-center text-sm text-text-muted"
    >
      Sin analitos todavía.
    </p>

    <div v-else class="space-y-4">
      <div v-for="group in groups" :key="group.sectionId ?? 'none'" class="space-y-2">
        <h4 class="text-xs font-semibold uppercase tracking-wide text-text-muted">
          {{ content.sectionName(group.sectionId) }}
        </h4>

        <UiExpandableList
          :items="group.items"
          :row-key="(item: ResultTemplateAnalyteRead) => item.id"
          :inactive="(item: ResultTemplateAnalyteRead) => !item.is_active"
        >
          <template #header="{ item }">
            <div>
              <p class="font-medium text-text">
                {{ content.analyteName(item.analyte_id) }}
              </p>
              <p class="text-xs text-text-muted">
                {{ detail(item) }} · Orden {{ item.sort_order }}
              </p>
            </div>
          </template>

          <template #summary="{ item }">
            <div class="flex items-center gap-2">
              <UiStatusBadge variant="primary" :label="RESULT_TYPE_LABELS[item.result_type] ?? item.result_type" />
              <UiStatusBadge v-if="!item.is_reportable" variant="neutral" label="No reportable" />
              <UiStatusBadge v-if="!content.isAnalyteActive(item.analyte_id)" variant="warning" label="Analito del catálogo inactivo" />
              <UiStatusBadge v-if="!item.is_active" :active="false" />
            </div>
          </template>

          <template #content="{ item }">
            <div class="flex flex-wrap items-center justify-between gap-2">
              <p class="text-sm text-text-muted">
                Requerido: {{ item.is_required ? 'Sí' : 'No' }} · Reportable: {{ item.is_reportable ? 'Sí' : 'No' }}
              </p>
              <div v-if="editable" class="flex gap-2">
                <UiButton variant="ghost" size="sm" @click="modal.openEdit(item)">
                  Editar analito
                </UiButton>
                <UiButton :variant="item.is_active ? 'danger-ghost' : 'ghost'" size="sm" @click="toggle.ask(item)">
                  {{ item.is_active ? 'Desactivar' : 'Reactivar' }}
                </UiButton>
              </div>
            </div>

            <ResultTemplateReferenceRanges :template-analyte="item" :content="content" :editable="editable" />
          </template>
        </UiExpandableList>
      </div>
    </div>

    <ResultTemplateAnalyteFormModal
      v-model:open="modal.open"
      :entity="modal.entity"
      :content="content"
      @saved="content.loadAnalytes()"
    />

    <UiToggleActiveModal
      :state="toggle"
      noun="el analito"
      :name="toggle.target ? content.analyteName(toggle.target.analyte_id) : undefined"
      deactivate-hint="Deja de contar al publicar este borrador."
    />
  </UiSection>
</template>
