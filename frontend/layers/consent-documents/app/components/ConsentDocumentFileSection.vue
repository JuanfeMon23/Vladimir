<script setup lang="ts">
/**
 * Archivo PDF de una versión de documento a firmar (editor de versión): estado
 * ("PDF adjunto" / "Sin archivo") con tamaño, tipo y huella SHA-256; Ver
 * (`UiPdfPreviewModal`) y Descargar siempre que haya archivo; Adjuntar /
 * Reemplazar / Quitar solo en borradores.
 *
 * Adjuntar y quitar son acciones inmediatas (PATCH con `file_base64`), fuera
 * del formulario del borrador: el base64 se genera al enviar y no se guarda en
 * ningún estado. Emite `changed` con la versión actualizada.
 */
import { base64ToBlob, fileToBase64, formatFileSize, PDF_CONTENT_TYPE, pdfFileErrorMessage, shortSha, validatePdfFile } from '#andromeda/utils/pdfFile'
import { downloadBlob } from '#andromeda/utils/downloadBlob'
import type { ConsentDocumentVersionRead } from '../types/consent-documents'
import { consentDocumentFilename, consentFileApiError } from '../utils/consentDocuments'

const props = defineProps<{
  version: ConsentDocumentVersionRead
  /** Código del documento (nombre de la descarga: `<codigo>-v<N>.pdf`). */
  documentCode: string
  /** Solo un borrador permite adjuntar, reemplazar o quitar. */
  editable: boolean
}>()

const emit = defineEmits<{ changed: [version: ConsentDocumentVersionRead] }>()

const consentDocumentsApi = useConsentDocuments()

const inputRef = ref<HTMLInputElement | null>(null)
const uploading = ref(false)
const downloading = ref(false)
const fileError = ref<string | null>(null)
const showPreview = ref(false)
const copied = ref(false)

const filename = computed(() => consentDocumentFilename(props.documentCode, props.version.version_number))
const loadFile = () => consentDocumentsApi.getVersionFile(props.version.id)

function pickFile() {
  inputRef.value?.click()
}

async function onFileSelected(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  fileError.value = null
  const reason = validatePdfFile(file)
  if (reason) {
    fileError.value = pdfFileErrorMessage(reason)
    return
  }
  uploading.value = true
  try {
    // El base64 vive solo durante el envío.
    const updated = await consentDocumentsApi.updateVersion(props.version.consent_document_id, props.version.id, {
      file_base64: await fileToBase64(file)
    })
    emit('changed', updated)
  } catch (err) {
    fileError.value = consentFileApiError(err) ?? (err instanceof Error && err.message ? err.message : 'No se pudo adjuntar el archivo.')
  } finally {
    uploading.value = false
  }
}

const removal = useConfirmAction(
  async () => {
    fileError.value = null
    emit('changed', await consentDocumentsApi.updateVersion(props.version.consent_document_id, props.version.id, { file_base64: null }))
  },
  { errorMessage: 'No se pudo quitar el archivo.', mapError: leoErrorMessage }
)

async function download() {
  downloading.value = true
  fileError.value = null
  try {
    const file = await loadFile()
    downloadBlob(base64ToBlob(file.base64, file.content_type || PDF_CONTENT_TYPE), filename.value)
  } catch (err) {
    fileError.value = err instanceof Error && err.message ? err.message : 'No se pudo descargar el archivo.'
  } finally {
    downloading.value = false
  }
}

async function copySha() {
  if (!props.version.file_sha256) return
  try {
    await navigator.clipboard.writeText(props.version.file_sha256)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch {
    fileError.value = 'No se pudo copiar la huella.'
  }
}
</script>

<template>
  <UiSection title="Archivo PDF" description="El PDF que firma el paciente. Es obligatorio para publicar la versión.">
    <UiAlert v-if="fileError" :message="fileError" />

    <div class="flex flex-wrap items-start justify-between gap-3 rounded-lg bg-surface px-4 py-3 shadow-sm">
      <div class="min-w-0 space-y-1">
        <UiStatusBadge v-if="version.has_file" variant="success" label="PDF adjunto" />
        <UiStatusBadge v-else variant="neutral" label="Sin archivo" />
        <p v-if="version.has_file" class="text-sm text-text-muted">
          {{ version.file_content_type ?? PDF_CONTENT_TYPE }} · {{ formatFileSize(version.file_size_bytes ?? 0) }}
        </p>
        <p v-if="version.has_file && version.file_sha256" class="flex flex-wrap items-center gap-2 text-xs text-text-muted">
          <span>SHA-256: <code :title="version.file_sha256">{{ shortSha(version.file_sha256) }}</code></span>
          <UiButton variant="ghost" size="sm" title="Copia la huella SHA-256 completa" @click="copySha">
            {{ copied ? 'Copiada' : 'Copiar huella' }}
          </UiButton>
        </p>
      </div>

      <div class="flex shrink-0 flex-wrap items-center gap-2">
        <template v-if="version.has_file">
          <UiButton variant="ghost" size="sm" @click="showPreview = true">
            Ver
          </UiButton>
          <UiButton variant="ghost" size="sm" :loading="downloading" @click="download">
            Descargar
          </UiButton>
        </template>
        <template v-if="editable">
          <UiButton variant="secondary" size="sm" :loading="uploading" @click="pickFile">
            {{ version.has_file ? 'Reemplazar' : 'Adjuntar PDF' }}
          </UiButton>
          <UiButton v-if="version.has_file" variant="danger-ghost" size="sm" @click="removal.ask(true)">
            Quitar
          </UiButton>
        </template>
        <input
          v-if="editable"
          ref="inputRef"
          type="file"
          accept="application/pdf,.pdf"
          class="sr-only"
          tabindex="-1"
          aria-label="Archivo PDF"
          @change="onFileSelected"
        >
      </div>
    </div>

    <UiPdfPreviewModal
      v-model:open="showPreview"
      :title="`Versión ${version.version_number}`"
      :filename="filename"
      :load="loadFile"
      :map-error="leoErrorMessage"
    />
    <UiConfirmModal
      v-model:open="removal.open"
      title="Quitar archivo"
      message="Se quitará el PDF de este borrador. Tendrás que adjuntar uno antes de publicar."
      confirm-label="Quitar"
      :loading="removal.loading"
      :error="removal.error"
      @confirm="removal.confirm()"
    />
  </UiSection>
</template>
