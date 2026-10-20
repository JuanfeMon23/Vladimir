<script setup lang="ts">
import { z } from 'zod'
import type {
  ResultTemplatePublishInactiveEntry,
  ResultTemplateRead,
  ResultTemplateVersionRead
} from '../../../../types/result-templates'

/**
 * Editor de una versión de plantilla de resultados (página propia:
 * excepción a la regla de modales). Datos generales (configuración del
 * reporte en JSON + notas), secciones, analitos y sus rangos de referencia;
 * todo editable solo en borrador. Publicar valida en el backend que cada
 * analito activo tenga los campos de su tipo (422 con `details.missing`) y
 * que nada de lo que usa esté desactivado (`details.inactive`); ambos se
 * listan en español bajo el error.
 */
definePageMeta({ layout: 'default', leo: { tag: RESULT_TEMPLATES_TAGS.view } })

const route = useRoute()
const resultTemplatesApi = useResultTemplates()

const templateId = route.params.id as string
const versionId = route.params.versionId as string

const template = ref<ResultTemplateRead | null>(null)
const saved = ref(false)

// `edit-version`: ajustes del reporte y notas; `edit-content`: secciones, analitos y rangos.
// Sin ellos, el editor (o esa parte) queda en solo lectura.
const canEditVersion = useCan(RESULT_TEMPLATES_TAGS.editVersion)
const canEditContent = useCan(RESULT_TEMPLATES_TAGS.editContent)
const generalEditable = computed(() => editor.isDraft && canEditVersion.value)
const contentEditable = computed(() => editor.isDraft && canEditContent.value)
const showPreview = ref(false)

const content = useResultTemplateVersionContent(templateId, versionId)

// --- Datos generales de la versión ---
const schema = z.object({
  report_settings: zJsonObject('La configuración del reporte'),
  change_notes: zOptionalText()
})

function toFormValues(version: ResultTemplateVersionRead) {
  return {
    report_settings: toJsonText(version.report_settings),
    change_notes: version.change_notes ?? ''
  }
}

const { submit, isSubmitting, formError, reset } = useZodForm(schema, {
  initialValues: { report_settings: '{}', change_notes: '' }
})

const editor = useVersionEditor<ResultTemplateVersionRead>({
  load: async () => (await resultTemplatesApi.listVersions(templateId, { page_size: 100 })).items.find(v => v.id === versionId),
  publish: () => resultTemplatesApi.publishVersion(templateId, versionId),
  retire: () => resultTemplatesApi.retireVersion(templateId, versionId),
  onChange: (version) => {
    saved.value = false
    reset(toFormValues(version))
  }
})

const onSubmit = submit(async (payload) => {
  saved.value = false
  editor.setVersion(await resultTemplatesApi.updateVersion(templateId, versionId, payload))
  saved.value = true
})

/** Líneas legibles de `details.missing` / `details.inactive` del 422 al publicar. */
function publishErrorLines(details: unknown) {
  return describeResultTemplatePublishErrors(details, {
    templateAnalyte: content.templateAnalyteName,
    reference: content.referenceName
  })
}

// Si hay opciones esperadas inactivas, se cargan las etiquetas de las opciones
// de los conjuntos de la versión para nombrarlas.
watch(() => editor.actionErrorDetails, (details) => {
  const inactive = (details as { inactive?: ResultTemplatePublishInactiveEntry[] } | null)?.inactive
  if (!Array.isArray(inactive) || !inactive.some(entry => entry.field === 'expected_option_id')) return
  content.loadOptionLabels(content.templateAnalytes.flatMap(item => (item.option_set_id ? [item.option_set_id] : [])))
})

onMounted(async () => {
  content.loadAll()
  try {
    template.value = await resultTemplatesApi.get(templateId)
  } catch {
    // El subtítulo es informativo; el editor funciona sin él.
  }
})
</script>

<template>
  <UiVersionEditor
    :editor="editor"
    :back-to="`/result-templates?open=${templateId}`"
    back-label="Volver a la plantilla"
    :permissions="RESULT_TEMPLATES_VERSION_PERMISSIONS"
    :subtitle="template ? `Plantilla: ${template.name} (${template.code})` : undefined"
  >
    <template #action-error="{ details }">
      <ul v-if="publishErrorLines(details).length" class="list-inside list-disc">
        <li v-for="line in publishErrorLines(details)" :key="line">
          {{ line }}
        </li>
      </ul>
    </template>

    <div class="max-w-4xl space-y-6">
      <UiSection title="Datos generales">
        <form class="space-y-4" novalidate @submit.prevent="onSubmit">
          <UiAlert v-if="formError" :message="formError" />
          <UiAlert v-if="saved" variant="success" message="Borrador guardado." />

          <fieldset :disabled="!generalEditable" class="grid min-w-0 grid-cols-1 gap-4">
            <UiFormField
              name="report_settings"
              label="Configuración del reporte (JSON)"
              hint="Objeto JSON, p. ej. { &quot;page_size&quot;: &quot;letter&quot; }"
            >
              <UiTextarea :rows="5" class="font-mono" />
            </UiFormField>
            <UiFormField name="change_notes" label="Notas del cambio">
              <UiTextarea :rows="2" />
            </UiFormField>
          </fieldset>

          <UiButton v-if="generalEditable" type="submit" :loading="isSubmitting">
            Guardar datos generales
          </UiButton>
        </form>
      </UiSection>

      <UiAlert v-if="content.catalogError" :message="content.catalogError" />

      <ResultTemplateSectionsPanel :content="content" :editable="contentEditable" />
      <ResultTemplateAnalytesPanel :content="content" :editable="contentEditable" />

      <UiSection title="Vista previa del reporte" description="Cómo se vería el reporte con la configuración actual (solo lectura)." divided>
        <template #actions>
          <UiButton variant="secondary" size="sm" :aria-expanded="showPreview" @click="showPreview = !showPreview">
            {{ showPreview ? 'Ocultar vista previa' : 'Mostrar vista previa' }}
          </UiButton>
        </template>
        <ResultTemplateReportPreview v-if="showPreview" :content="content" />
      </UiSection>
    </div>
  </UiVersionEditor>
</template>
