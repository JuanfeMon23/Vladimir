<script setup lang="ts">
import type { ResultTemplateVersionContent } from '../composables/useResultTemplateVersionContent'
import { REFERENCE_RANGE_AGE_UNIT_LABELS, REFERENCE_RANGE_SEX_LABELS } from '../types/result-templates'
import type { ReferenceRangeRead, ResultTemplateAnalyteRead } from '../types/result-templates'

/**
 * Rangos de referencia de un analito de plantilla (panel expandido del
 * analito en el editor de versión): lista, crear/editar en modal y
 * desactivar/reactivar con motivo (nada se elimina). Se cargan al montarse
 * (al expandir el analito), con los inactivos para "Mostrar inactivos".
 */
const props = defineProps<{
  templateAnalyte: ResultTemplateAnalyteRead
  content: ResultTemplateVersionContent
  editable: boolean
}>()

const api = useResultTemplates()

const ranges = ref<ReferenceRangeRead[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const modal = useEntityModal<ReferenceRangeRead>()
const showInactive = ref(false)
const visibleRanges = computed(() => (showInactive.value ? ranges.value : ranges.value.filter(range => range.is_active)))

async function load() {
  loading.value = true
  error.value = null
  try {
    ranges.value = await api.listReferenceRanges(props.content.templateId, props.content.versionId, props.templateAnalyte.id, { include_inactive: true })
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No se pudieron cargar los rangos.'
  } finally {
    loading.value = false
  }
}

const toggle = useToggleActive(
  async (range: ReferenceRangeRead, change) => {
    await api.updateReferenceRange(props.content.templateId, props.content.versionId, props.templateAnalyte.id, range.id, change)
    await load()
  },
  { errorMessage: 'No se pudo cambiar el estado del rango.' }
)

function between(low: number | null, high: number | null) {
  return `${low ?? '–'} a ${high ?? '–'}`
}

function describe(range: ReferenceRangeRead) {
  const parts = [`Sexo: ${REFERENCE_RANGE_SEX_LABELS[range.sex] ?? range.sex}`]
  if (range.age_min !== null || range.age_max !== null) {
    const unit = range.age_unit ? ` ${REFERENCE_RANGE_AGE_UNIT_LABELS[range.age_unit] ?? range.age_unit}` : ''
    parts.push(`Edad: ${between(range.age_min, range.age_max)}${unit.toLowerCase()}`)
  }
  if (range.condition) parts.push(range.condition)
  return parts.join(' · ')
}

onMounted(load)
</script>

<template>
  <UiSection title="Rangos de referencia">
    <template #actions>
      <UiCheckbox v-model="showInactive" label="Mostrar inactivos" />
      <UiButton v-if="editable" variant="secondary" size="sm" @click="modal.openCreate()">
        Agregar rango
      </UiButton>
    </template>

    <UiAlert v-if="error" :message="error" />
    <UiItemList
      :items="visibleRanges"
      :row-key="(range: ReferenceRangeRead) => range.id"
      :loading="loading"
      :inactive="(range: ReferenceRangeRead) => !range.is_active"
      empty-message="Sin rangos todavía."
    >
      <template #default="{ item }">
        <p class="text-text">
          {{ describe(item) }}
        </p>
        <p class="text-text-muted">
          <span v-if="item.low !== null || item.high !== null">Rango: {{ between(item.low, item.high) }}</span>
          <span v-if="item.critical_low !== null || item.critical_high !== null"> · Crítico: {{ between(item.critical_low, item.critical_high) }}</span>
          <span v-if="item.expected_boolean !== null"> · Esperado: {{ item.expected_boolean ? 'Verdadero' : 'Falso' }}</span>
          <span v-if="item.display_text"> · {{ item.display_text }}</span>
        </p>
      </template>
      <template #trailing="{ item }">
        <UiStatusBadge v-if="!item.is_active" :active="false" />
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

    <ResultTemplateReferenceRangeFormModal
      v-model:open="modal.open"
      :entity="modal.entity"
      :template-analyte="templateAnalyte"
      :content="content"
      @saved="load"
    />

    <UiToggleActiveModal :state="toggle" noun="el rango" :name="toggle.target ? describe(toggle.target) : undefined" />
  </UiSection>
</template>
