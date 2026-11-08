import type { VersionPermissionTags } from '~/utils/versioning'

/**
 * Qué acciones de versionado puede hacer el usuario (reactivo). Cada acción
 * exige su tag; sin tag no se permite (fail-closed).
 */
export function useVersionPermissions(tags: () => VersionPermissionTags | undefined) {
  const session = useLeoSession()
  const allowed = (pick: (tags: VersionPermissionTags) => string | undefined) => computed(() => {
    const tag = pick(tags() ?? {})
    return !!tag && session.can(tag)
  })
  return reactive({
    create: allowed(tags => tags.create),
    edit: allowed(tags => tags.edit),
    publish: allowed(tags => tags.publish),
    retire: allowed(tags => tags.retire)
  })
}
