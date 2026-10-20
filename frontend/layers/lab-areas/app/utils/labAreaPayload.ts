/**
 * Cuerpo del PATCH de un área según los permisos del usuario (ver
 * `buildGuardedUpdate`, núcleo). `null`: nada que enviar.
 */
export function buildLabAreaUpdate(
  values: { code: string, name: string, description?: string | null, is_active: boolean, activity_reason?: string | null },
  entity: { is_active: boolean },
  can: { canEdit: boolean, canChangeStatus: boolean }
): Record<string, unknown> | null {
  return buildGuardedUpdate(values, entity, can)
}
