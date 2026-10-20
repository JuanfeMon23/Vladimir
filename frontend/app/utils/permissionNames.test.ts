import { describe, expect, it } from 'vitest'
import { forbiddenMessage, permissionName } from './permissionNames'

describe('permissionNames', () => {
  it('devuelve el nombre legible de un tag conocido', () => {
    expect(permissionName('vladimir.lab-areas.create')).toBe('Crear áreas de laboratorio')
  })

  it('un tag desconocido no tiene nombre', () => {
    expect(permissionName('vladimir.x.y')).toBeNull()
    expect(permissionName(undefined)).toBeNull()
  })

  it('forbiddenMessage nombra el permiso; sin nombre usa el mensaje de respaldo', () => {
    expect(forbiddenMessage('vladimir.lab-areas.edit', 'x')).toBe('No tienes permiso para: Editar áreas de laboratorio')
    expect(forbiddenMessage('vladimir.x.y', 'Sin permiso.')).toBe('Sin permiso.')
    expect(forbiddenMessage(undefined, 'Sin permiso.')).toBe('Sin permiso.')
  })
})
