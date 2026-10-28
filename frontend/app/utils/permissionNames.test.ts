import { beforeAll, describe, expect, it } from 'vitest'
import permissions from '../generated/permissions.json'
import { PERMISSION_NAMES } from './permissionNames'

// `permissionName` y `forbiddenMessage` vienen de leo-client; aquí se verifica el mapa de Vladimir registrado.
beforeAll(() => registerPermissionNames(PERMISSION_NAMES))

describe('permissionNames', () => {
  it('devuelve el nombre legible de un tag conocido', () => {
    expect(permissionName('vladimir.lab-areas.create')).toBe(permissions.modules.find(m => m.slug === 'lab-areas')!.actions.find(a => a.verb === 'create')!.name)
  })

  it('un tag desconocido no tiene nombre', () => {
    expect(permissionName('vladimir.x.y')).toBeNull()
    expect(permissionName(undefined)).toBeNull()
  })

  it('todos los tags asignables del contrato tienen nombre legible; los eventos no', () => {
    const actions = permissions.modules.flatMap(module => module.actions)
    for (const action of actions) {
      expect(permissionName(action.tag), action.tag).toBe(action.assignable ? action.name : null)
    }
    expect(forbiddenMessage({ action: 'vladimir.lab-tests.set-sample-types' }, 'x')).toMatch(/^No tienes permiso para: .+/)
  })

  it('el evento settings.update no se concede ni se muestra', () => {
    expect(permissionName('vladimir.settings.update')).toBeNull()
  })

  it('forbiddenMessage nombra el permiso; sin nombre usa el mensaje de respaldo', () => {
    expect(forbiddenMessage({ action: 'vladimir.lab-areas.edit' }, 'x')).toBe(`No tienes permiso para: ${PERMISSION_NAMES['vladimir.lab-areas.edit']}`)
    expect(forbiddenMessage({ action: 'vladimir.x.y' }, 'Sin permiso.')).toBe('Sin permiso.')
    expect(forbiddenMessage(undefined, 'Sin permiso.')).toBe('Sin permiso.')
  })
})
