<script setup lang="ts">
import { z } from 'zod'
import {
  CONSENT_DOCUMENT_SIGNERS,
  CONSENT_DOCUMENT_SIGNER_LABELS
} from '../../../../types/consent-documents'
import type { ConsentDocumentRead, ConsentDocumentVersionRead } from '../../../../types/consent-documents'
import { describeConsentPublishErrors } from '../../../../utils/consentDocuments'

/**
 * Editor de una versión de documento a firmar (página propia: excepción a la
 * regla de modales). Solo un borrador es editable. El PDF se adjunta, ve y
 * descarga en `ConsentDocumentFileSection`; sin PDF no se puede publicar.
 */
definePageMeta({ layout: 'default', leo: { tag: CONSENT_DOCUMENTS_TAGS.view } })

const route = useRoute()
const consentDocumentsApi = useConsentDocuments()

const documentId = route.params.id as string
const versionId = route.params.versionId as string

const consentDocument = ref<ConsentDocumentRead | null>(null)
const saved = ref(false)

// Sin `edit-version` el editor (texto, firmante y PDF) queda en solo lectura.
const canEditVersion = useCan(CONSENT_DOCUMENTS_TAGS.editVersion)
const editable = computed(() => editor.isDraft && canEditVersion.value)

const PUBLISH_BLOCKED_NO_FILE = 'Adjunta el PDF antes de publicar.'

const signerOptions = toSelectOptions(CONSENT_DOCUMENT_SIGNER_LABELS)

const schema = z.object({
  signer: zRequiredEnum(CONSENT_DOCUMENT_SIGNERS, 'Selecciona quién firma.'),
  content: zRequiredText('El contenido es obligatorio.'),
  change_notes: zOptionalText()
})

function toFormValues(version: ConsentDocumentVersionRead) {
  return {
    signer: version.signer,
    content: version.content,
    change_notes: version.change_notes ?? ''
  }
}

const { submit, isSubmitting, formError, reset } = useZodForm(schema, {
  initialValues: { signer: '', content: '', change_notes: '' }
})

const editor = useVersionEditor<ConsentDocumentVersionRead>({
  load: async () => (await consentDocumentsApi.listVersions(documentId, { page_size: 100 })).items.find(v => v.id === versionId),
  publish: () => consentDocumentsApi.publishVersion(documentId, versionId),
  retire: () => consentDocumentsApi.retireVersion(documentId, versionId),
  onChange: (version) => {
    saved.value = false
    reset(toFormValues(version))
  }
})

const onSubmit = submit(async (payload) => {
  saved.value = false
  editor.setVersion(await consentDocumentsApi.updateVersion(documentId, versionId, payload))
  saved.value = true
})

onMounted(async () => {
  try {
    consentDocument.value = await consentDocumentsApi.get(documentId)
  } catch {
    // El subtítulo es informativo; el editor funciona sin él.
  }
})
</script>

<template>
  <UiVersionEditor
    :editor="editor"
    :back-to="`/consent-documents?open=${documentId}`"
    back-label="Volver al documento"
    :permissions="CONSENT_DOCUMENTS_VERSION_PERMISSIONS"
    :subtitle="consentDocument ? `Documento: ${consentDocument.name} (${consentDocument.code})` : undefined"
    :publish-blocked-reason="editor.version && !editor.version.has_file ? PUBLISH_BLOCKED_NO_FILE : null"
  >
    <template #action-error="{ details }">
      <ul v-if="describeConsentPublishErrors(details).length" class="list-disc pl-5">
        <li v-for="line in describeConsentPublishErrors(details)" :key="line">
          {{ line }}
        </li>
      </ul>
    </template>

    <div class="max-w-3xl space-y-5">
      <ConsentDocumentFileSection
        v-if="editor.version"
        :version="editor.version"
        :document-code="consentDocument?.code ?? 'documento'"
        :editable="editable"
        @changed="editor.patchVersion"
      />

      <form class="space-y-5" novalidate @submit.prevent="onSubmit">
        <UiAlert v-if="formError" :message="formError" />
        <UiAlert v-if="saved" variant="success" message="Borrador guardado." />

        <fieldset :disabled="!editable" class="grid min-w-0 grid-cols-1 gap-4">
          <UiFormField name="signer" label="Firmante" required>
            <UiSelect :options="signerOptions" placeholder="Seleccionar firmante" />
          </UiFormField>
          <UiFormField name="change_notes" label="Notas del cambio">
            <UiTextarea :rows="2" />
          </UiFormField>
          <UiFormField
            name="content"
            label="Contenido"
            hint="Markdown en texto plano; sin vista previa renderizada."
            required
          >
            <UiTextarea :rows="16" />
          </UiFormField>
        </fieldset>

        <UiButton v-if="editable" type="submit" :loading="isSubmitting">
          Guardar borrador
        </UiButton>
      </form>
    </div>
  </UiVersionEditor>
</template>
