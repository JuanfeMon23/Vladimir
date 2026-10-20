interface FormValues {
  code: string
  name: string
  description?: string | null
  is_active: boolean
  activity_reason?: string | null
}

/**
 * Cuerpo del PATCH de un área según los permisos del usuario. El backend exige
 * `edit` por los datos y `change-status` en cuanto llega `is_active`, así que
 * cada grupo viaja solo si el usuario puede y (para el estado) si cambió.
 * `null`: nada que enviar.
 */
export function buildLabAreaUpdate(
  values: FormValues,
  entity: { is_active: boolean },
  can: { canEdit: boolean, canChangeStatus: boolean }
): Record<string, unknown> | null {
  const body: Record<string, unknown> = {}
  if (can.canEdit) {
    body.code = values.code
    body.name = values.name
    body.description = values.description
  }
  if (can.canChangeStatus && values.is_active !== entity.is_active) {
    body.is_active = values.is_active
    if (values.activity_reason) body.activity_reason = values.activity_reason
  }
  return Object.keys(body).length ? body : null
}
