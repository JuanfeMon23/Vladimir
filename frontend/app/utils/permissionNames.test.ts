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

  it('todos los tags de los 8 módulos protegidos tienen nombre legible', () => {
    const tags = [
      'staff.view', 'staff.create', 'staff.edit', 'staff.change-status',
      'lab-tests.view', 'lab-tests.create', 'lab-tests.edit', 'lab-tests.change-status',
      'lab-tests.set-preconditions', 'lab-tests.set-sample-types', 'lab-tests.set-consent-documents',
      'preconditions.view', 'preconditions.create', 'preconditions.edit', 'preconditions.change-status',
      'preconditions.add-item'
    ]
    const versioning = ['create-version', 'edit-version', 'publish-version', 'retire-version']
    const crud = ['view', 'create', 'edit', 'change-status']
    for (const module of ['print-labels', 'result-templates', 'consent-documents']) {
      for (const verb of [...crud, ...versioning]) tags.push(`${module}.${verb}`)
    }
    for (const verb of [...crud, 'add-type']) tags.push(`samples.${verb}`)
    for (const verb of ['edit-content', 'manage-units', 'manage-analytes', 'manage-option-sets']) tags.push(`result-templates.${verb}`)
    for (const tag of tags) expect(permissionName(`vladimir.${tag}`), tag).not.toBeNull()
    expect(forbiddenMessage('vladimir.lab-tests.set-sample-types', 'x')).toBe('No tienes permiso para: Asignar tipos de muestra a exámenes')
  })

  it('forbiddenMessage nombra el permiso; sin nombre usa el mensaje de respaldo', () => {
    expect(forbiddenMessage('vladimir.lab-areas.edit', 'x')).toBe('No tienes permiso para: Editar áreas de laboratorio')
    expect(forbiddenMessage('vladimir.x.y', 'Sin permiso.')).toBe('Sin permiso.')
    expect(forbiddenMessage(undefined, 'Sin permiso.')).toBe('Sin permiso.')
  })
})
