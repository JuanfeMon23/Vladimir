<script setup lang="ts">
/**
 * Selector "entidad versionada + versión publicada" del formulario de examen
 * (etiqueta de impresión y plantilla de resultados): primero se elige la
 * entidad (control local, no es campo del payload) y luego una de sus
 * versiones publicadas (`?status=published`), que sí es el campo `name` del
 * `useZodForm` del ancestro (`print_label_version_id` /
 * `result_template_version_id`).
 *
 * Al montar, si el campo ya tiene una versión, pide esa versión con su
 * dueña (`GET /<entidad>-versions/{id}`) y la conserva en las opciones
 * aunque ya no esté publicada. Cambiar de entidad limpia la versión elegida.
 * Solo se ofrecen entidades activas; la dueña de la versión ya asignada se
 * sigue mostrando aunque esté inactiva ("(inactivo)").
 */
import { useFieldValue, useSetFieldValue } from 'vee-validate'
import type { UiSelectOption } from '#andromeda/components/ui/UiSelect.vue'
import type { LabTestCatalogOption, LabTestVersionOption, LabTestVersionWithOwner } from '../types/lab-tests'

const props = defineProps<{
  /** Campo del formulario con el id de la versión. */
  name: string
  ownerLabel: string
  ownerPlaceholder: string
  /** Mensaje si la entidad elegida no tiene versiones publicadas. */
  emptyVersionsHint: string
  loadOwners: () => Promise<LabTestCatalogOption[]>
  /** Versiones publicadas de una entidad. */
  loadPublishedVersions: (ownerId: string) => Promise<LabTestVersionOption[]>
  /** Una versión con su entidad dueña. */
  loadVersion: (versionId: string) => Promise<LabTestVersionWithOwner>
}>()

const versionId = useFieldValue<string | null>(() => props.name)
const setVersionId = useSetFieldValue<string | null>(() => props.name)

const owners = ref<LabTestCatalogOption[]>([])
const ownerId = ref<string | null>(null)
/** Versión que ya tenía el examen al abrir (con su dueña). */
const assigned = ref<LabTestVersionWithOwner | null>(null)
/** Versiones publicadas de la entidad elegida. */
const published = ref<LabTestVersionOption[]>([])
const loading = ref(true)
const loadError = ref<string | null>(null)

function messageOf(err: unknown, fallback: string) {
  return err instanceof Error && err.message ? err.message : fallback
}

/** Solo entidades activas, más la dueña de la versión ya asignada aunque esté inactiva. */
const ownerOptions = computed<UiSelectOption[]>(() =>
  activeSelectOptions(owners.value, owner => `${owner.name} (${owner.code})`, assigned.value?.owner.id)
)

/** Publicadas, más la versión ya asignada aunque ya no lo esté (para no ocultarla). */
const versionOptions = computed<UiSelectOption[]>(() => {
  const list = [...published.value]
  const current = assigned.value
  if (current && current.id === versionId.value && current.owner.id === ownerId.value && !list.some(v => v.id === current.id)) {
    list.push(current)
  }
  return list
    .sort((a, b) => a.version_number - b.version_number)
    .map(version => ({
      value: version.id,
      label: version.status === 'published'
        ? `Versión ${version.version_number}`
        : `Versión ${version.version_number} (${VERSION_STATUS_LABELS[version.status].toLowerCase()})`
    }))
})

const versionHint = computed(() => {
  if (!ownerId.value) return `Elige primero: ${props.ownerLabel.toLowerCase()}.`
  if (versionOptions.value.length === 0) return props.emptyVersionsHint
  return undefined
})

async function loadPublished(id: string) {
  try {
    published.value = await props.loadPublishedVersions(id)
  } catch (err) {
    loadError.value = messageOf(err, 'No se pudieron cargar las versiones.')
  }
}

async function selectOwner(id: string | null) {
  ownerId.value = id
  setVersionId(null)
  published.value = []
  if (id) await loadPublished(id)
}

onMounted(async () => {
  try {
    const current = versionId.value
    const [list, version] = await Promise.all([props.loadOwners(), current ? props.loadVersion(current) : null])
    owners.value = list
    if (version) {
      assigned.value = version
      ownerId.value = version.owner.id
      // La dueña puede no venir en el catálogo (p. ej. paginación): se agrega.
      if (!list.some(owner => owner.id === version.owner.id)) owners.value = [...list, version.owner]
      await loadPublished(version.owner.id)
    }
  } catch (err) {
    loadError.value = messageOf(err, 'No se pudieron cargar las opciones.')
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
    <UiAlert v-if="loadError" :message="loadError" class="sm:col-span-2" />
    <UiFormField :label="ownerLabel" hint="Opcional">
      <UiSelect
        :model-value="ownerId ?? ''"
        :options="ownerOptions"
        :empty-label="ownerPlaceholder"
        :disabled="loading"
        @update:model-value="selectOwner($event || null)"
      />
    </UiFormField>
    <UiFormField :name="name" label="Versión publicada" :hint="versionHint">
      <UiSelect
        :options="versionOptions"
        empty-label="Sin versión"
        :disabled="loading || !ownerId"
      />
    </UiFormField>
  </div>
</template>
