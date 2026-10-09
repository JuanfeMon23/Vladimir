<script setup lang="ts">
/**
 * Vista previa de un PDF en un `UiModal`: el archivo se pide SOLO al abrir
 * (`load`, carga perezosa; sin caché), se convierte en un Blob y se muestra
 * embebido (`<object>` sobre un Blob URL) con fallback "Descargar" si el
 * navegador no sabe mostrarlo. El Blob URL se revoca al cerrar o desmontar.
 *
 * El base64 que devuelve `load` solo vive en la función que arma el Blob; en
 * el estado reactivo queda únicamente la URL.
 */
import { base64ToBlob, downloadBlob, PDF_CONTENT_TYPE } from '~/utils/pdfFile'

export interface UiPdfPreviewFile {
  base64: string
  content_type?: string | null
}

const open = defineModel<boolean>('open', { required: true })

const props = withDefaults(
  defineProps<{
    title?: string
    /** Nombre de la descarga (`<codigo>-v<N>.pdf`). */
    filename: string
    /** Pide el archivo al abrir el modal. */
    load: () => Promise<UiPdfPreviewFile>
  }>(),
  { title: 'Vista previa del PDF' }
)

const blobUrl = ref<string | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
let blob: Blob | null = null
let token = 0

function release() {
  if (blobUrl.value) URL.revokeObjectURL(blobUrl.value)
  blobUrl.value = null
  blob = null
}

async function start() {
  const current = ++token
  release()
  loading.value = true
  error.value = null
  try {
    const file = await props.load()
    if (current !== token) return
    blob = base64ToBlob(file.base64, file.content_type || PDF_CONTENT_TYPE)
    blobUrl.value = URL.createObjectURL(blob)
  } catch (err) {
    if (current !== token) return
    error.value = err instanceof Error && err.message ? err.message : 'No se pudo cargar el archivo.'
  } finally {
    if (current === token) loading.value = false
  }
}

watch(open, (isOpen) => {
  if (isOpen) {
    void start()
  } else {
    token++
    release()
    loading.value = false
  }
}, { immediate: true })

onBeforeUnmount(() => {
  token++
  release()
})

function download() {
  if (blob) downloadBlob(blob, props.filename)
}
</script>

<template>
  <UiModal v-model:open="open" :title="title" :description="filename" size="xl">
    <div v-if="loading" class="flex items-center gap-2 py-8 text-sm text-text-muted">
      <UiSpinner size="sm" color="primary" />
      <span>Cargando archivo…</span>
    </div>
    <UiAlert v-else-if="error" :message="error" />
    <object
      v-else-if="blobUrl"
      :data="blobUrl"
      :type="PDF_CONTENT_TYPE"
      :aria-label="title"
      class="h-[70vh] w-full rounded-md bg-default-100"
    >
      <div class="space-y-3 p-6 text-sm text-text-muted">
        <p>Tu navegador no puede mostrar el PDF aquí.</p>
        <UiButton variant="secondary" size="sm" @click="download">
          Descargar
        </UiButton>
      </div>
    </object>

    <template #footer="{ close }">
      <UiButton variant="secondary" @click="close">
        Cerrar
      </UiButton>
      <UiButton :disabled="!blobUrl" @click="download">
        Descargar
      </UiButton>
    </template>
  </UiModal>
</template>
