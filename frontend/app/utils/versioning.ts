/**
 * Piezas compartidas de las entidades versionadas (ciclo
 * `draft -> published -> retired`, `app.core.versioning` en el backend):
 * print-labels, result-templates, consent-documents.
 */

import type { VersionBadge, VersionStatus, VersionTimelineEntry } from '#andromeda/types/versioning'

// `VersionStatus`, `VersionBadge`, `VersionTimelineEntry` y `VERSION_STATUS_LABELS/VARIANTS` vienen de Andromeda.
export type { VersionBadge, VersionStatus, VersionTimelineEntry }

/** Campos comunes de toda `*VersionRead` del backend. */
export interface VersionRecord {
  id: string
  version_number: number
  status: VersionStatus
  published_at: string | null
  change_notes: string | null
}

/**
 * Tags de Leo de las acciones de versionado de un módulo. El núcleo no conoce
 * los tags de ningún módulo: cada layer pasa los suyos; sin tag, la acción
 * no se restringe (módulo sin proteger).
 */
export interface VersionPermissionTags {
  create?: string
  edit?: string
  publish?: string
  retire?: string
}

export function toVersionTimelineEntry(version: VersionRecord): VersionTimelineEntry {
  return {
    id: version.id,
    versionNumber: version.version_number,
    status: version.status,
    publishedAt: version.published_at,
    changeNotes: version.change_notes
  }
}

/**
 * Códigos de examen que impiden retirar una versión: 409 `version_in_use`
 * de `POST .../versions/{id}/retire` (`details.lab_test_codes`). Lista vacía
 * para cualquier otro error.
 */
export function versionInUseCodes(err: unknown): string[] {
  if (!(err instanceof LeoApiError) || err.code !== 'version_in_use') return []
  const details = err.details as { lab_test_codes?: unknown } | null | undefined
  const codes = details?.lab_test_codes
  return Array.isArray(codes) ? codes.filter((code): code is string => typeof code === 'string') : []
}
