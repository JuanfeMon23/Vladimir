import permissions from '../generated/permissions.json'

/**
 * Nombres legibles de los permisos (tags) de Vladimir, para mensajes al
 * usuario ("No tienes permiso para: …"). Se registran en leo-client con
 * `registerPermissionNames` (plugin `permissionNames.ts`). Se DERIVAN del
 * contrato generado por el backend (`generated/permissions.json`, ver README):
 * no se editan a mano. Los eventos de auditoría (no asignables) no tienen nombre.
 */
export const PERMISSION_NAMES: Record<string, string> = Object.fromEntries(
  permissions.modules.flatMap(module =>
    module.actions.filter(action => action.assignable).map(action => [action.tag, action.name])
  )
)
