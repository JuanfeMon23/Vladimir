/** Campos de estado de un PATCH: viajan solo con `change-status`; el resto son datos (`edit`). */
const STATUS_KEYS = ['is_active', 'activity_reason']

/**
 * Cuerpo del PATCH de una entidad con `is_active` según los permisos del
 * usuario. El backend exige `edit` por los datos y `change-status` en cuanto
 * llega `is_active`, así que cada grupo viaja solo si el usuario puede y (el
 * estado) si cambió. `null`: nada que enviar.
 */
export function buildGuardedUpdate(
  values: { is_active: boolean, activity_reason?: string | null } & Record<string, unknown>,
  entity: { is_active: boolean },
  can: { canEdit: boolean, canChangeStatus: boolean }
): Record<string, unknown> | null {
  const body: Record<string, unknown> = {}
  if (can.canEdit) {
    for (const [key, value] of Object.entries(values)) {
      if (!STATUS_KEYS.includes(key)) body[key] = value
    }
  }
  if (can.canChangeStatus && values.is_active !== entity.is_active) {
    body.is_active = values.is_active
    if (values.activity_reason) body.activity_reason = values.activity_reason
  }
  return Object.keys(body).length ? body : null
}
