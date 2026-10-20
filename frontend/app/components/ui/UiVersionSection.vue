<script setup lang="ts">
/**
 * Sección "Versiones" de una entidad versionada, dentro de su modal de detalle
 * (slot `#extra` de `UiFormModal`): carga las versiones, crea un borrador
 * nuevo y abre su editor (página propia), y publica / retira (con
 * confirmación) desde la línea de tiempo. Común a print-labels,
 * result-templates y consent-documents; cada layer solo pasa su `api`.
 */
import type { VersionBadge, VersionPermissionTags, VersionRecord } from '~/utils/versioning'

export interface UiVersionSectionApi {
  list: () => Promise<VersionRecord[]>
  /**
   * Crea un borrador. `isFirst` indica que la entidad no tiene versiones: el
   * backend exige entonces todos los campos obligatorios (la layer manda sus
   * valores por defecto); si no, clona la última versión.
   */
  create: (isFirst: boolean) => Promise<{ id: string }>
  publish: (versionId: string) => Promise<unknown>
  retire: (versionId: string) => Promise<unknown>
  /** Ruta del editor de una versión (`/<modulo>/<id>/versions/<versionId>`). */
  editorPath: (versionId: string) => string
  /** Chips propios del módulo junto al estado (p. ej. "PDF adjunto"). */
  badges?: (version: VersionRecord) => VersionBadge[]
  /**
   * Motivo por el que NO se puede publicar esa versión (p. ej. "Adjunta el
   * PDF antes de publicar."); `null` = se puede. Deshabilita Publicar y
   * muestra el motivo bajo la versión.
   */
  publishBlockedReason?: (version: VersionRecord) => string | null
}

const props = withDefaults(
  defineProps<{
    api: UiVersionSectionApi
    title?: string
    description?: string
    /** Tags de las acciones de versionado; cada botón exige el suyo. */
    permissions?: VersionPermissionTags
  }>(),
  {
    permissions: () => ({}),
    title: 'Versiones',
    description: 'El contenido se edita por versión; solo un borrador es editable.'
  }
)

const can = useVersionPermissions(() => props.permissions)
const versions = ref<VersionRecord[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const creating = ref(false)
const publishingId = ref<string | null>(null)

const entries = computed(() => versions.value.map(version => ({
  ...toVersionTimelineEntry(version),
  badges: props.api.badges?.(version),
  hint: version.status === 'draft' ? props.api.publishBlockedReason?.(version) ?? null : null
})))
const hasDraft = computed(() => versions.value.some(version => version.status === 'draft'))

function messageOf(err: unknown, fallback: string) {
  return err instanceof Error && err.message ? err.message : fallback
}

async function load() {
  loading.value = true
  error.value = null
  try {
    versions.value = await props.api.list()
  } catch (err) {
    error.value = messageOf(err, 'No se pudieron cargar las versiones.')
  } finally {
    loading.value = false
  }
}

async function createVersion() {
  creating.value = true
  error.value = null
  try {
    const created = await props.api.create(versions.value.length === 0)
    await navigateTo(props.api.editorPath(created.id))
  } catch (err) {
    error.value = messageOf(err, 'No se pudo crear la versión.')
  } finally {
    creating.value = false
  }
}

async function publish(versionId: string) {
  publishingId.value = versionId
  error.value = null
  try {
    await props.api.publish(versionId)
    await load()
  } catch (err) {
    error.value = messageOf(err, 'No se pudo publicar la versión.')
  } finally {
    publishingId.value = null
  }
}

const retirement = useConfirmAction(
  async (versionId: string) => {
    await props.api.retire(versionId)
    await load()
  },
  { errorMessage: 'No se pudo retirar la versión.' }
)

onMounted(load)
</script>

<template>
  <UiSection :title="title" :description="description" divided>
    <template #actions>
      <UiButton
        v-if="can.create"
        size="sm"
        :loading="creating"
        :disabled="loading || hasDraft"
        :title="hasDraft ? 'Ya hay un borrador: edítalo o publícalo antes de crear otra versión.' : undefined"
        @click="createVersion"
      >
        Nueva versión
      </UiButton>
    </template>

    <UiAlert v-if="error" :message="error" />

    <div v-if="loading" class="flex items-center gap-2 px-1 py-2 text-sm text-text-muted">
      <UiSpinner size="sm" color="primary" />
      <span>Cargando versiones…</span>
    </div>

    <UiVersionTimeline v-else :versions="entries">
      <template #actions="{ version }">
        <UiButton :to="api.editorPath(version.id)" variant="ghost" size="sm">
          {{ version.status === 'draft' && can.edit ? 'Editar' : 'Ver' }}
        </UiButton>
        <UiButton
          v-if="version.status === 'draft' && can.publish"
          variant="secondary"
          size="sm"
          :loading="publishingId === version.id"
          :disabled="Boolean(version.hint)"
          :title="version.hint ?? undefined"
          @click="publish(version.id)"
        >
          Publicar
        </UiButton>
        <UiButton
          v-if="version.status === 'published' && can.retire"
          variant="danger-ghost"
          size="sm"
          @click="retirement.ask(version.id)"
        >
          Retirar
        </UiButton>
      </template>
    </UiVersionTimeline>

    <UiVersionRetireModal :state="retirement" />
  </UiSection>
</template>
