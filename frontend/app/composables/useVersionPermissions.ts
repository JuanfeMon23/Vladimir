import type { VersionPermissionTags } from '~/utils/versioning'

/**
 * Qué acciones de versionado puede hacer el usuario (reactivo). Cada acción
 * exige su tag; sin tag no se permite (fail-closed).
 */
export function useVersionPermissions(tags: () => VersionPermissionTags | undefined) {
  const session = useLeoSession()
  const allowed = (pick: (t: VersionPermissionTags) => string | undefined) => computed(() => {
    const tag = pick(tags() ?? {})
    return !!tag && session.can(tag)
  })
  return reactive({
    create: allowed(t => t.create),
    edit: allowed(t => t.edit),
    publish: allowed(t => t.publish),
    retire: allowed(t => t.retire)
  })
}
