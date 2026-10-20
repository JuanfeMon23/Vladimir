import { describe, expect, it } from 'vitest'
import { buildLabAreaUpdate } from './labAreaPayload'

const entity = { is_active: true }
const values = { code: 'HEM', name: 'Hematología', description: 'd', is_active: true, activity_reason: '' }
const all = { canEdit: true, canChangeStatus: true }

describe('buildLabAreaUpdate', () => {
  it('con edit envía los datos y NO is_active si no cambió (evita exigir change-status)', () => {
    expect(buildLabAreaUpdate(values, entity, all)).toEqual({ code: 'HEM', name: 'Hematología', description: 'd' })
  })

  it('con change-status y un cambio de estado envía is_active y el motivo', () => {
    const next = { ...values, is_active: false, activity_reason: 'cierre' }
    expect(buildLabAreaUpdate(next, entity, all)).toEqual({
      code: 'HEM', name: 'Hematología', description: 'd', is_active: false, activity_reason: 'cierre'
    })
  })

  it('sin change-status nunca envía is_active', () => {
    const next = { ...values, is_active: false }
    expect(buildLabAreaUpdate(next, entity, { canEdit: true, canChangeStatus: false })).not.toHaveProperty('is_active')
  })

  it('sin edit solo envía el estado', () => {
    const next = { ...values, name: 'otro', is_active: false, activity_reason: '' }
    expect(buildLabAreaUpdate(next, entity, { canEdit: false, canChangeStatus: true })).toEqual({ is_active: false })
  })

  it('sin nada que enviar devuelve null', () => {
    expect(buildLabAreaUpdate(values, entity, { canEdit: false, canChangeStatus: true })).toBeNull()
    expect(buildLabAreaUpdate(values, entity, { canEdit: false, canChangeStatus: false })).toBeNull()
  })
})
