/**
 * Nombres legibles de los permisos (tags) de Vladimir, para mensajes al
 * usuario ("No tienes permiso para: …"). Son los mismos del catálogo
 * sincronizado en Leo; cada módulo protegido agrega aquí los suyos.
 */
const PERMISSION_NAMES: Record<string, string> = {
  'vladimir.lab-areas.view': 'Consultar áreas de laboratorio',
  'vladimir.lab-areas.create': 'Crear áreas de laboratorio',
  'vladimir.lab-areas.edit': 'Editar áreas de laboratorio',
  'vladimir.lab-areas.change-status': 'Activar o desactivar áreas de laboratorio',
  'vladimir.lab-areas.assign-manager': 'Asignar encargado de un área de laboratorio'
}

export function permissionName(tag: string | undefined | null): string | null {
  return (tag && PERMISSION_NAMES[tag]) || null
}

/** Mensaje de un 403 `forbidden`: nombra el permiso si se conoce; si no, el de respaldo. */
export function forbiddenMessage(tag: string | undefined | null, fallback: string): string {
  const name = permissionName(tag)
  return name ? `No tienes permiso para: ${name}` : fallback
}
