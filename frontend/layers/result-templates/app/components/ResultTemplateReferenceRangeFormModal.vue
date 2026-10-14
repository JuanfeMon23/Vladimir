<script setup lang="ts">
import { z } from 'zod'
import type { UiSelectOption } from '#andromeda/components/ui/UiSelect.vue'
import type { ResultTemplateVersionContent } from '../composables/useResultTemplateVersionContent'
import {
  REFERENCE_RANGE_AGE_UNITS,
  REFERENCE_RANGE_AGE_UNIT_LABELS,
  REFERENCE_RANGE_SEXES,
  REFERENCE_RANGE_SEX_LABELS
} from '../types/result-templates'
import type { ReferenceRangeRead, ReferenceRangeTypedField, ResultOptionRead, ResultTemplateAnalyteRead } from '../types/result-templates'

/**
 * Crear o editar un rango de referencia de un analito de plantilla (solo en
 * borrador). Un único formulario para crear y editar. Los campos tipados
 * visibles dependen del `result_type` del analito
 * (`resultTemplateRangeFields`: numérico/calculado → límites; cualitativo/
 * semicuantitativo → opción esperada; booleano → booleano esperado; texto →
 * solo texto a mostrar e interpretación; titulación → todos). Los no
 * admitidos no se validan ni se envían.
 */
const props = defineProps<{
  entity: ReferenceRangeRead | null
  templateAnalyte: ResultTemplateAnalyteRead
  content: ResultTemplateVersionContent
}>()
const emit = defineEmits<{ saved: [] }>()
const open = defineModel<boolean>('open', { required: true })

/** Campos tipados que admite el tipo de resultado del analito. */
const allowedFields = computed(() => new Set<ReferenceRangeTypedField>(resultTemplateRangeFields(props.templateAnalyte.result_type)))
const has = (field: ReferenceRangeTypedField) => allowedFields.value.has(field)

const sexOptions = toSelectOptions(REFERENCE_RANGE_SEX_LABELS)
const ageUnitOptions = toSelectOptions(REFERENCE_RANGE_AGE_UNIT_LABELS)
const booleanOptions: UiSelectOption[] = [
  { value: 'true', label: 'Verdadero' },
  { value: 'false', label: 'Falso' }
]

/** `''` → `null`, `'true'`/`'false'` → booleano (desde un `<UiSelect>`). */
const zOptionalBooleanChoice = z
  .enum(['', 'true', 'false'])
  .optional()
  .transform(value => (value ? value === 'true' : null))

/** Si ambos límites están, `low <= high`; el error va al campo superior. */
function orderedPair(low: number | null, high: number | null, path: string, ctx: z.RefinementCtx, message: string) {
  if (low !== null && high !== null && low > high) {
    ctx.addIssue({ code: z.ZodIssueCode.custom, path: [path], message })
  }
}

const schema = z
  .object({
    sex: zRequiredEnum(REFERENCE_RANGE_SEXES, 'Selecciona el sexo.'),
    age_min: zOptionalNumber({ min: 0 }),
    age_max: zOptionalNumber({ min: 0 }),
    age_unit: zOptionalEnum(REFERENCE_RANGE_AGE_UNITS),
    condition: zOptionalText(255),
    low: zOptionalNumber(),
    high: zOptionalNumber(),
    critical_low: zOptionalNumber(),
    critical_high: zOptionalNumber(),
    expected_option_id: zOptionalId(),
    expected_boolean: zOptionalBooleanChoice,
    display_text: zOptionalText(255),
    interpretation: zOptionalText()
  })
  .superRefine((value, ctx) => {
    orderedPair(value.age_min, value.age_max, 'age_max', ctx, 'Debe ser mayor o igual a la edad mínima.')
    // Los límites solo se validan si el tipo de resultado los admite (ocultos no se envían).
    if (!has('low')) return
    orderedPair(value.low, value.high, 'high', ctx, 'Debe ser mayor o igual al mínimo.')
    orderedPair(value.critical_low, value.critical_high, 'critical_high', ctx, 'Debe ser mayor o igual al crítico mínimo.')
  })

function numberText(value: number | null | undefined) {
  return value === null || value === undefined ? '' : String(value)
}

function booleanChoice(value: boolean | null | undefined): '' | 'true' | 'false' {
  if (value === null || value === undefined) return ''
  return value ? 'true' : 'false'
}

const { submit, isSubmitting, formError } = useZodForm(schema, {
  initialValues: () => {
    const source = props.entity
    return {
      sex: source?.sex ?? 'any',
      age_min: numberText(source?.age_min),
      age_max: numberText(source?.age_max),
      age_unit: source?.age_unit ?? '',
      condition: source?.condition ?? '',
      low: numberText(source?.low),
      high: numberText(source?.high),
      critical_low: numberText(source?.critical_low),
      critical_high: numberText(source?.critical_high),
      expected_option_id: source?.expected_option_id ?? '',
      expected_boolean: booleanChoice(source?.expected_boolean),
      display_text: source?.display_text ?? '',
      interpretation: source?.interpretation ?? ''
    }
  },
  resetOn: open
})

// Opciones del conjunto del analito, para "opción esperada": solo activas,
// más la ya elegida aunque se haya desactivado.
const optionCatalog = ref<ResultOptionRead[]>([])
const expectedOptions = computed<UiSelectOption[]>(() =>
  activeSelectOptions(optionCatalog.value, option => option.label, props.entity?.expected_option_id)
)
watch(open, async (isOpen) => {
  const optionSetId = props.templateAnalyte.option_set_id
  if (!isOpen || !optionSetId || !has('expected_option_id')) return
  try {
    const page = await useResultOptionSets().listOptions(optionSetId, { page_size: 200 }, { cacheTtl: CATALOG_CACHE_TTL })
    optionCatalog.value = [...page.items].sort((a, b) => a.sort_order - b.sort_order)
  } catch {
    optionCatalog.value = []
  }
}, { immediate: true })

const onSubmit = submit(async (values) => {
  const api = useResultTemplates()
  const { templateId, versionId } = props.content
  const payload = pickResultTemplateRangeValues(values, props.templateAnalyte.result_type)
  if (props.entity) {
    await api.updateReferenceRange(templateId, versionId, props.templateAnalyte.id, props.entity.id, payload)
  } else {
    await api.createReferenceRange(templateId, versionId, props.templateAnalyte.id, payload)
  }
  emit('saved')
  open.value = false
})
</script>

<template>
  <UiFormModal
    v-model:open="open"
    :activity="entity ? { entityType: 'reference_ranges', entityId: entity.id } : null"
    :title="entity ? 'Editar rango de referencia' : 'Nuevo rango de referencia'"
    :description="content.analyteName(templateAnalyte.analyte_id)"
    size="lg"
    :submitting="isSubmitting"
    :form-error="formError"
    :submit-label="entity ? 'Guardar cambios' : 'Agregar'"
    @submit="onSubmit"
  >
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-4">
      <UiFormField name="sex" label="Sexo" required>
        <UiSelect :options="sexOptions" />
      </UiFormField>
      <UiFormField name="age_min" label="Edad mín.">
        <UiTextInput type="number" step="any" min="0" />
      </UiFormField>
      <UiFormField name="age_max" label="Edad máx.">
        <UiTextInput type="number" step="any" min="0" />
      </UiFormField>
      <UiFormField name="age_unit" label="Unidad de edad">
        <UiSelect :options="ageUnitOptions" empty-label="Sin unidad" />
      </UiFormField>

      <template v-if="has('low')">
        <UiFormField name="low" label="Mínimo">
          <UiTextInput type="number" step="any" />
        </UiFormField>
        <UiFormField name="high" label="Máximo">
          <UiTextInput type="number" step="any" />
        </UiFormField>
        <UiFormField name="critical_low" label="Crítico mín.">
          <UiTextInput type="number" step="any" />
        </UiFormField>
        <UiFormField name="critical_high" label="Crítico máx.">
          <UiTextInput type="number" step="any" />
        </UiFormField>
      </template>

      <UiFormField
        v-if="has('expected_option_id')"
        name="expected_option_id"
        label="Opción esperada"
        class="sm:col-span-2"
        :hint="templateAnalyte.option_set_id ? undefined : 'El analito no tiene conjunto de opciones.'"
      >
        <UiSelect :options="expectedOptions" empty-label="Sin definir" :disabled="!templateAnalyte.option_set_id" />
      </UiFormField>
      <UiFormField v-if="has('expected_boolean')" name="expected_boolean" label="Booleano esperado" class="sm:col-span-2">
        <UiSelect :options="booleanOptions" empty-label="Sin definir" />
      </UiFormField>

      <UiFormField name="condition" label="Condición" class="sm:col-span-2" hint="P. ej. embarazo, ayuno.">
        <UiTextInput />
      </UiFormField>
      <UiFormField name="display_text" label="Texto a mostrar" class="sm:col-span-2">
        <UiTextInput />
      </UiFormField>
      <UiFormField name="interpretation" label="Interpretación" class="sm:col-span-4">
        <UiTextarea :rows="2" />
      </UiFormField>
    </div>
  </UiFormModal>
</template>
