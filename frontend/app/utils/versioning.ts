/**
 * Piezas compartidas de las entidades versionadas (ciclo
 * `draft -> published -> retired`, `app.core.versioning` en el backend):
 * print-labels, result-templates, consent-documents.
 */
import { ApiRequestError } from '~/composables/useApi'

export type VersionStatus = 'draft' | 'published' | 'retired'

/** Campos comunes de toda `*VersionRead` del backend. */
export interface VersionRecord {
  id: string
  version_number: number
  status: VersionStatus
  published_at: string | null
  change_notes: string | null
}

/** Chip extra de una versión (p. ej. "PDF adjunto"), junto a su estado. */
export interface VersionBadge {
  label: string
  variant: 'success' | 'danger' | 'warning' | 'neutral' | 'primary'
}

/** Entrada de `UiVersionTimeline` (camelCase, independiente del módulo). */
export interface VersionTimelineEntry {
  id: string
  versionNumber: number
  status: VersionStatus
  publishedAt?: string | null
  changeNotes?: string | null
  /** Chips propios del módulo, tras el de estado. */
  badges?: VersionBadge[]
  /** Aviso corto bajo la versión (p. ej. por qué no se puede publicar). */
  hint?: string | null
}

export const VERSION_STATUS_LABELS: Record<VersionStatus, string> = {
  draft: 'Borrador',
  published: 'Publicada',
  retired: 'Retirada'
}

export const VERSION_STATUS_VARIANTS: Record<VersionStatus, 'neutral' | 'success' | 'danger'> = {
  draft: 'neutral',
  published: 'success',
  retired: 'danger'
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
  if (!(err instanceof ApiRequestError) || err.code !== 'version_in_use') return []
  const details = err.details as { lab_test_codes?: unknown } | null | undefined
  const codes = details?.lab_test_codes
  return Array.isArray(codes) ? codes.filter((code): code is string => typeof code === 'string') : []
}
