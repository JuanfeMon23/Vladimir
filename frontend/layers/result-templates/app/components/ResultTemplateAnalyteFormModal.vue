<script setup lang="ts">
import { z } from 'zod'
import type { ResultTemplateVersionContent } from '../composables/useResultTemplateVersionContent'
import type { ResultTemplateAnalyteCreate, ResultTemplateAnalyteRead } from '../types/result-templates'

/**
 * Agregar o editar un analito de una versión de plantilla (solo en
 * borrador). Los campos dependen del tipo de resultado: unidad/decimales
 * (numérico y calculado), conjunto de opciones (cualitativo, semicuantitativo
 * y título), fórmula (calculado; los problemas del backend, por `reason`, salen
 * en el campo); los que no aplican se envían en `null`. Al elegir un
 * analito con la unidad vacía, se precarga su unidad por defecto. Los
 * selectores ofrecen solo elementos activos (más el valor ya guardado).
 */
import { useSetFieldValue } from 'vee-validate'
const props = defineProps<{
  entity: ResultTemplateAnalyteRead | null
  content: ResultTemplateVersionContent
}>()
const emit = defineEmits<{ saved: [] }>()
const open = defineModel<boolean>('open', { required: true })

const schema = z.object({
  analyte_id: zRequiredId('Selecciona un analito.'),
  section_id: zOptionalId(),
  sort_order: zRequiredNumber('El orden es obligatorio.', { min: 0, integer: true }),
  result_type: zRequiredText('Selecciona un tipo de resultado.', 64),
  unit_id: zOptionalId(),
  decimals: zOptionalNumber({ min: 0, integer: true }),
  option_set_id: zOptionalId(),
  formula: zOptionalText(),
  default_value: zOptionalText(255),
  is_required: z.boolean(),
  is_reportable: z.boolean()
})

const nextSortOrder = computed(() =>
  props.content.templateAnalytes.reduce((max, item) => Math.max(max, item.sort_order + 1), 0)
)

const { submit, isSubmitting, formError, values, setFieldError } = useZodForm(schema, {
  initialValues: () => {
    const source = props.entity
    return {
      analyte_id: source?.analyte_id ?? '',
      section_id: source?.section_id ?? '',
      sort_order: source?.sort_order ?? nextSortOrder.value,
      result_type: source?.result_type ?? '',
      unit_id: source?.unit_id ?? '',
      decimals: source?.decimals ?? '',
      option_set_id: source?.option_set_id ?? '',
      formula: source?.formula ?? '',
      default_value: source?.default_value ?? '',
      is_required: source?.is_required ?? true,
      is_reportable: source?.is_reportable ?? true
    }
  },
  resetOn: open
})

const resultTypeOptions = computed(() => props.content.resultTypes.optionsFor(props.entity?.result_type))
const behavior = computed(() => props.content.resultTypeBehavior(values.result_type))
/** Unidad y decimales: el backend los exige al publicar si el tipo `uses_unit`. */
const usesUnit = computed(() => behavior.value?.uses_unit === true)
const usesOptionSet = computed(() => behavior.value?.uses_option_set === true)
const isCalculated = computed(() => behavior.value?.uses_formula === true)

// Al elegir un analito, si la unidad está vacía se precarga su unidad por defecto.
const setUnitId = useSetFieldValue<string>('unit_id')
watch(() => values.analyte_id, (analyteId, previous) => {
  if (!open.value || !analyteId || analyteId === previous || values.unit_id) return
  const defaultUnitId = props.content.analyteDefaultUnitId(analyteId)
  if (defaultUnitId) setUnitId(defaultUnitId)
})

const analyteOptions = computed(() => props.content.analyteOptionsFor(props.entity?.analyte_id))
const sectionOptions = computed(() => props.content.sectionOptionsFor(props.entity?.section_id))
const optionSetOptions = computed(() => props.content.optionSetOptionsFor(props.entity?.option_set_id))
const unitOptions = computed(() => props.content.unitOptionsFor(props.entity?.unit_id))
/** Códigos de los analitos activos de la versión que la fórmula puede usar. */
const formulaCodes = computed(() => props.content.formulaCodes(props.entity?.id))

const onSubmit = submit(async (form) => {
  const payload: ResultTemplateAnalyteCreate = {
    ...form,
    unit_id: usesUnit.value ? form.unit_id : null,
    decimals: usesUnit.value ? form.decimals : null,
    option_set_id: usesOptionSet.value ? form.option_set_id : null,
    formula: isCalculated.value ? form.formula : null
  }
  const api = useResultTemplates()
  const { templateId, versionId } = props.content
  try {
    if (props.entity) await api.updateTemplateAnalyte(templateId, versionId, props.entity.id, payload)
    else await api.createTemplateAnalyte(templateId, versionId, payload)
  } catch (err) {
    // 422 de la fórmula: un mensaje en español por problema, en el campo.
    const problems = err instanceof LeoApiError ? formulaProblemMessages(err.details) : []
    if (!problems.length) throw err
    setFieldError('formula', problems.join(' '))
    return
  }
  emit('saved')
  open.value = false
})
</script>

<template>
  <UiFormModal
    v-model:open="open"
    :activity="entity ? { entityType: 'result_template_analytes', entityId: entity.id } : null"
    :title="entity ? 'Editar analito de la plantilla' : 'Agregar analito'"
    size="lg"
    :submitting="isSubmitting"
    :form-error="formError"
    :submit-label="entity ? 'Guardar cambios' : 'Agregar'"
    @submit="onSubmit"
  >
    <UiAlert v-if="content.catalogError" :message="content.catalogError" />
    <UiAlert v-if="content.resultTypes.error" :message="content.resultTypes.error" />

    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <UiFormField name="analyte_id" label="Analito" required>
        <UiSelect :options="analyteOptions" placeholder="Seleccionar analito" />
      </UiFormField>
      <UiFormField name="section_id" label="Sección">
        <UiSelect :options="sectionOptions" empty-label="Sin sección" />
      </UiFormField>
      <UiFormField name="result_type" label="Tipo de resultado" required>
        <UiSelect :options="resultTypeOptions" placeholder="Seleccionar tipo" />
      </UiFormField>
      <UiFormField name="sort_order" label="Orden" required>
        <UiTextInput type="number" step="1" min="0" />
      </UiFormField>

      <template v-if="usesUnit">
        <UiFormField name="unit_id" label="Unidad (UCUM)" hint="Obligatoria para publicar con este tipo de resultado.">
          <UiSelect :options="unitOptions" empty-label="Sin unidad" />
        </UiFormField>
        <UiFormField name="decimals" label="Decimales" hint="Obligatorios para publicar con este tipo de resultado.">
          <UiTextInput type="number" step="1" min="0" />
        </UiFormField>
      </template>

      <UiFormField
        v-if="usesOptionSet"
        name="option_set_id"
        label="Conjunto de opciones"
        class="sm:col-span-2"
        hint="Obligatorio para publicar con este tipo de resultado."
      >
        <UiSelect :options="optionSetOptions" empty-label="Sin conjunto" />
      </UiFormField>

      <UiFormField
        v-if="isCalculated"
        name="formula"
        label="Fórmula"
        class="sm:col-span-2"
        hint="Obligatoria para publicar. Usa códigos de analito (con llaves si tienen guiones o puntos: {LDL-C}), números, + − * / y paréntesis."
      >
        <UiTextInput />
      </UiFormField>
      <p v-if="isCalculated" class="text-xs text-text-muted sm:col-span-2">
        Códigos que puedes usar:
        <template v-if="formulaCodes.length">{{ formulaCodes.join(', ') }}</template>
        <template v-else>ningún otro analito activo en esta versión.</template>
      </p>

      <UiFormField name="default_value" label="Valor por defecto" class="sm:col-span-2">
        <UiTextInput />
      </UiFormField>
    </div>

    <div class="flex flex-wrap gap-6">
      <UiFormField name="is_required">
        <UiCheckbox label="Requerido" />
      </UiFormField>
      <UiFormField name="is_reportable">
        <UiCheckbox label="Reportable" description="Aparece en el reporte impreso." />
      </UiFormField>
    </div>
  </UiFormModal>
</template>
