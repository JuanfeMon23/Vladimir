<script setup lang="ts">
import { z } from 'zod'
import {
  PRINT_LABEL_OUTPUT_FORMATS,
  PRINT_LABEL_OUTPUT_FORMAT_LABELS
} from '../../../../types/print-labels'
import type { PrintLabelRead, PrintLabelVersionRead } from '../../../../types/print-labels'

/**
 * Editor de una versión de etiqueta (página propia: excepción a la regla de
 * modales). Solo un borrador es editable; publicar/retirar también se puede
 * desde el modal de la etiqueta.
 */
definePageMeta({ layout: 'default', leo: { tag: PRINT_LABELS_TAGS.view } })

const route = useRoute()
const printLabelsApi = usePrintLabels()

const labelId = route.params.id as string
const versionId = route.params.versionId as string

const label = ref<PrintLabelRead | null>(null)
const saved = ref(false)

// Sin `edit-version` el editor queda en solo lectura.
const canEditVersion = useCan(PRINT_LABELS_TAGS.editVersion)
const editable = computed(() => editor.isDraft && canEditVersion.value)

const outputFormatOptions = toSelectOptions(PRINT_LABEL_OUTPUT_FORMAT_LABELS)

const schema = z.object({
  width_mm: zRequiredNumber('El ancho es obligatorio.', { min: 1 }),
  height_mm: zRequiredNumber('El alto es obligatorio.', { min: 1 }),
  dpi: zRequiredNumber('Los DPI son obligatorios.', { min: 1, integer: true }),
  copies: zRequiredNumber('Las copias son obligatorias.', { min: 1, integer: true }),
  output_format: zRequiredEnum(PRINT_LABEL_OUTPUT_FORMATS, 'Selecciona un formato de salida.'),
  barcode_type: zOptionalText(32),
  template_content: zRequiredText('El contenido de la plantilla es obligatorio.'),
  placeholders: zJsonObject('Los placeholders'),
  change_notes: zOptionalText()
})

function toFormValues(version: PrintLabelVersionRead) {
  return {
    width_mm: version.width_mm,
    height_mm: version.height_mm,
    dpi: version.dpi,
    copies: version.copies,
    output_format: version.output_format,
    barcode_type: version.barcode_type ?? '',
    template_content: version.template_content,
    placeholders: toJsonText(version.placeholders),
    change_notes: version.change_notes ?? ''
  }
}

const { submit, isSubmitting, formError, reset, values } = useZodForm(schema, {
  initialValues: {
    width_mm: '',
    height_mm: '',
    dpi: '',
    copies: '',
    output_format: '',
    barcode_type: '',
    template_content: '',
    placeholders: '{}',
    change_notes: ''
  }
})

const editor = useVersionEditor<PrintLabelVersionRead>({
  load: async () => (await printLabelsApi.listVersions(labelId, { page_size: 100 })).items.find(v => v.id === versionId),
  publish: () => printLabelsApi.publishVersion(labelId, versionId),
  retire: () => printLabelsApi.retireVersion(labelId, versionId),
  onChange: (version) => {
    saved.value = false
    reset(toFormValues(version))
  }
})

const onSubmit = submit(async (payload) => {
  saved.value = false
  editor.setVersion(await printLabelsApi.updateVersion(labelId, versionId, payload))
  saved.value = true
})

/** Vista previa simple: escapa HTML y resalta los placeholders `{{...}}`. */
const previewHtml = computed(() => {
  const escaped = String(values.template_content ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  return escaped.replace(
    /\{\{\s*[\w.-]+\s*\}\}/g,
    match => `<span class="rounded-sm bg-primary-100 px-1 text-primary-700">${match}</span>`
  )
})

onMounted(async () => {
  try {
    label.value = await printLabelsApi.get(labelId)
  } catch {
    // El subtítulo es informativo; el editor funciona sin él.
  }
})
</script>

<template>
  <UiVersionEditor
    :editor="editor"
    :back-to="`/print-labels?open=${labelId}`"
    back-label="Volver a la etiqueta"
    :permissions="PRINT_LABELS_VERSION_PERMISSIONS"
    :subtitle="label ? `Etiqueta: ${label.name} (${label.code})` : undefined"
  >
    <form class="max-w-3xl space-y-5" novalidate @submit.prevent="onSubmit">
      <UiAlert v-if="formError" :message="formError" />
      <UiAlert v-if="saved" variant="success" message="Borrador guardado." />

      <fieldset :disabled="!editable" class="grid min-w-0 grid-cols-1 gap-4 sm:grid-cols-2">
        <UiFormField name="width_mm" label="Ancho (mm)" required>
          <UiTextInput type="number" step="0.01" min="1" />
        </UiFormField>
        <UiFormField name="height_mm" label="Alto (mm)" required>
          <UiTextInput type="number" step="0.01" min="1" />
        </UiFormField>
        <UiFormField name="dpi" label="DPI" required>
          <UiTextInput type="number" step="1" min="1" />
        </UiFormField>
        <UiFormField name="copies" label="Copias" required>
          <UiTextInput type="number" step="1" min="1" />
        </UiFormField>
        <UiFormField name="output_format" label="Formato de salida" required>
          <UiSelect :options="outputFormatOptions" placeholder="Seleccionar formato" />
        </UiFormField>
        <UiFormField name="barcode_type" label="Tipo de código de barras">
          <UiTextInput />
        </UiFormField>
        <UiFormField name="change_notes" label="Notas del cambio" class="sm:col-span-2">
          <UiTextarea :rows="2" />
        </UiFormField>
        <UiFormField name="template_content" label="Contenido de la plantilla" class="sm:col-span-2" required>
          <UiTextarea :rows="8" class="font-mono" />
        </UiFormField>
        <UiFormField
          name="placeholders"
          label="Placeholders (JSON)"
          class="sm:col-span-2"
          hint="Objeto JSON, p. ej. { &quot;patient_name&quot;: &quot;Nombre del paciente&quot; }"
        >
          <UiTextarea :rows="6" class="font-mono" />
        </UiFormField>
      </fieldset>

      <UiButton v-if="editable" type="submit" :loading="isSubmitting">
        Guardar borrador
      </UiButton>
    </form>

    <UiSection
      title="Vista previa de la plantilla"
      description="Contenido crudo con los placeholders resaltados; no renderiza ZPL/HTML real."
      divided
      class="max-w-3xl"
    >
      <pre
        class="overflow-x-auto rounded-lg bg-surface-muted p-4 text-xs text-text"
        v-html="previewHtml"
      />
    </UiSection>
  </UiVersionEditor>
</template>
