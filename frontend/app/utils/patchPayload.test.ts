import { describe, expect, it } from 'vitest'
import { buildGuardedUpdate } from './patchPayload'

const entity = { is_active: true }
const values = { code: 'X', name: 'Nombre', is_active: true, activity_reason: '' }
const all = { canEdit: true, canChangeStatus: true }

describe('buildGuardedUpdate', () => {
  it('con edit envía todos los datos y NO is_active si no cambió', () => {
    expect(buildGuardedUpdate(values, entity, all)).toEqual({ code: 'X', name: 'Nombre' })
  })

  it('con change-status y un cambio de estado envía is_active y el motivo', () => {
    expect(buildGuardedUpdate({ ...values, is_active: false, activity_reason: 'cierre' }, entity, all)).toEqual({
      code: 'X', name: 'Nombre', is_active: false, activity_reason: 'cierre'
    })
  })

  it('sin motivo no envía activity_reason', () => {
    expect(buildGuardedUpdate({ ...values, is_active: false }, entity, all)).not.toHaveProperty('activity_reason')
  })

  it('sin change-status nunca envía is_active', () => {
    const body = buildGuardedUpdate({ ...values, is_active: false }, entity, { canEdit: true, canChangeStatus: false })
    expect(body).not.toHaveProperty('is_active')
  })

  it('sin edit solo envía el estado', () => {
    expect(buildGuardedUpdate({ ...values, name: 'otro', is_active: false }, entity, { canEdit: false, canChangeStatus: true }))
      .toEqual({ is_active: false })
  })

  it('sin nada que enviar devuelve null', () => {
    expect(buildGuardedUpdate(values, entity, { canEdit: false, canChangeStatus: true })).toBeNull()
    expect(buildGuardedUpdate(values, entity, { canEdit: false, canChangeStatus: false })).toBeNull()
  })
})
