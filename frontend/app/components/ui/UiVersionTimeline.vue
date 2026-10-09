<script setup lang="ts" generic="V extends UiVersionTimelineEntry">
/**
 * Línea de tiempo de versiones del núcleo. Usada por módulos con entidades
 * versionadas (ciclo `draft -> published -> retired`, ver `app.core.versioning`
 * en el backend): print-labels, result-templates, consent-documents.
 *
 * Pinta la lista ordenada por `versionNumber` desc, con `UiVersionStatusBadge`
 * por estado. Las acciones por versión van en el slot `#actions`; el panel
 * estándar (crear / editar / publicar / retirar) es `UiVersionSection`.
 */
import type { VersionStatus, VersionTimelineEntry } from '~/utils/versioning'

export type UiVersionTimelineStatus = VersionStatus
export type UiVersionTimelineEntry = VersionTimelineEntry

const props = defineProps<{
  versions: V[]
}>()

const statusDot: Record<UiVersionTimelineStatus, string> = {
  draft: 'bg-default-400',
  published: 'bg-success-500',
  retired: 'bg-danger-400'
}

function formatDate(value: string | null | undefined) {
  if (!value) return null
  return new Date(value).toLocaleString('es', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const sortedVersions = computed(() => [...props.versions].sort((a, b) => b.versionNumber - a.versionNumber))
</script>

<template>
  <ol class="relative space-y-3">
    <li
      v-for="(version, index) in sortedVersions"
      :key="version.id"
      class="relative pl-7"
    >
      <span
        v-if="index < sortedVersions.length - 1"
        class="absolute bottom-[-0.75rem] left-[0.4375rem] top-5 w-px bg-default-200"
        aria-hidden="true"
      />
      <span
        class="absolute left-0 top-4 h-3.5 w-3.5 rounded-full ring-4 ring-background"
        :class="statusDot[version.status]"
        aria-hidden="true"
      />
      <div class="flex flex-wrap items-start justify-between gap-4 rounded-lg bg-surface px-4 py-3 shadow-sm">
        <div class="space-y-1">
          <div class="flex items-center gap-2">
            <span class="text-sm font-semibold text-text">
              Versión {{ version.versionNumber }}
            </span>
            <UiVersionStatusBadge :status="version.status" />
            <UiStatusBadge
              v-for="badge in version.badges"
              :key="badge.label"
              :variant="badge.variant"
              :label="badge.label"
            />
          </div>
          <p v-if="formatDate(version.publishedAt)" class="text-xs text-text-muted">
            Publicada: {{ formatDate(version.publishedAt) }}
          </p>
          <p v-if="version.changeNotes" class="text-sm text-text-muted">
            {{ version.changeNotes }}
          </p>
          <p v-if="version.hint" class="text-xs text-text-muted">
            {{ version.hint }}
          </p>
        </div>

        <div class="flex shrink-0 items-center gap-2">
          <slot name="actions" :version="version" />
        </div>
      </div>
    </li>

    <li v-if="versions.length === 0" class="rounded-lg border-2 border-dashed border-default-200 px-4 py-6 text-center text-sm text-text-muted">
      Sin versiones todavía.
    </li>
  </ol>
</template>
