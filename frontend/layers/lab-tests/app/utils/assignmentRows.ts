/**
 * Filas de una pestaña de asignaciones del examen (precondiciones, tipos de
 * muestra, documentos), según las reglas de activación:
 * - Solo lo AGREGADO debe estar activo: el catálogo ofrece solo elementos
 *   activos.
 * - Una asignación vigente a un elemento que luego se desactivó se conserva
 *   (seleccionada, marcada "inactivo").
 * - Las asignaciones quitadas (el PUT es un diff: lo quitado se desactiva)
 *   se muestran como historial con "Mostrar inactivos"; si el elemento sigue
 *   activo, su fila del catálogo se puede volver a marcar.
 */

/** Elemento del catálogo (todos, activos e inactivos, para poder nombrarlos). */
export interface LabTestAssignmentCatalogEntry {
  id: string
  label: string
  isActive: boolean
  /** Fila hija (ítem de una precondición). */
  indent?: boolean
}

/** Asignación del examen (`GET …?include_inactive=true`). */
export interface LabTestAssignmentLink {
  id: string
  /** `false` = asignación quitada (historial). */
  isActive: boolean
  sortOrder: number
  /** Etiqueta si el elemento no está en el catálogo. */
  fallbackLabel?: string
  /** Id de la fila de asignación (para su historial de actividad). */
  linkId?: string
}

export interface LabTestAssignmentRow {
  /** Posición en `rows` del formulario de la pestaña. */
  index: number
  id: string
  label: string
  indent: boolean
  /** Asignación vigente (fila marcada al cargar). */
  assigned: boolean
  /** Se puede marcar/desmarcar. */
  selectable: boolean
  /** El elemento del catálogo está desactivado (o ya no existe). */
  elementInactive: boolean
  /** Hubo una asignación que se quitó. */
  linkInactive: boolean
  /** Id de la asignación (vigente o, si no hay, la quitada); `null` si nunca se asignó. */
  linkId: string | null
}

export function buildLabTestAssignmentRows(
  links: readonly LabTestAssignmentLink[],
  catalog: readonly LabTestAssignmentCatalogEntry[]
): LabTestAssignmentRow[] {
  const byId = new Map(catalog.map(entry => [entry.id, entry]))
  const active = [...links].filter(link => link.isActive).sort((a, b) => a.sortOrder - b.sortOrder)
  const activeIds = new Set(active.map(link => link.id))
  const removedIds = new Set(links.filter(link => !link.isActive && !activeIds.has(link.id)).map(link => link.id))
  const removedLinkId = new Map(links.filter(link => !link.isActive).map(link => [link.id, link.linkId ?? null]))
  const rows: Omit<LabTestAssignmentRow, 'index'>[] = []

  for (const link of active) {
    const entry = byId.get(link.id)
    rows.push({
      id: link.id,
      label: entry?.label ?? link.fallbackLabel ?? link.id,
      indent: entry?.indent ?? false,
      assigned: true,
      selectable: true,
      elementInactive: !entry?.isActive,
      linkInactive: false,
      linkId: link.linkId ?? null
    })
  }

  for (const entry of catalog) {
    if (!entry.isActive || activeIds.has(entry.id)) continue
    rows.push({
      id: entry.id,
      label: entry.label,
      indent: entry.indent ?? false,
      assigned: false,
      selectable: true,
      elementInactive: false,
      linkInactive: removedIds.has(entry.id),
      linkId: removedLinkId.get(entry.id) ?? null
    })
  }

  for (const link of links) {
    if (link.isActive || activeIds.has(link.id) || byId.get(link.id)?.isActive) continue
    if (rows.some(row => row.id === link.id)) continue
    const entry = byId.get(link.id)
    rows.push({
      id: link.id,
      label: entry?.label ?? link.fallbackLabel ?? link.id,
      indent: entry?.indent ?? false,
      assigned: false,
      selectable: false,
      elementInactive: true,
      linkInactive: true,
      linkId: link.linkId ?? null
    })
  }

  return rows.map((row, index) => ({ ...row, index }))
}

/** Filas a pintar: el historial no seleccionable solo con "Mostrar inactivos". */
export function visibleLabTestAssignmentRows(rows: readonly LabTestAssignmentRow[], showInactive: boolean) {
  return rows.filter(row => row.selectable || showInactive)
}

/**
 * Body del PUT de una pestaña de asignaciones (reemplaza el set completo):
 * solo las filas marcadas, sin el campo `selected` del formulario.
 */
export function labTestAssignmentPayload<R extends { selected: boolean }>(rows: readonly R[]): Omit<R, 'selected'>[] {
  return rows
    .filter(row => row.selected)
    .map(({ selected: _selected, ...rest }) => rest)
}

/** Igual que `labTestAssignmentPayload`, con `sort_order` = orden en la lista (desde 1). */
export function labTestOrderedAssignmentPayload<R extends { selected: boolean }>(rows: readonly R[]) {
  return labTestAssignmentPayload(rows).map((row, index) => ({ ...row, sort_order: index + 1 }))
}
