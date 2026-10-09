import { describe, expect, it, vi } from 'vitest'
import { useToggleActive } from './useToggleActive'

interface Item { id: string, is_active: boolean }

describe('useToggleActive', () => {
  it('ask() abre para el objetivo y reinicia el motivo', () => {
    const toggle = useToggleActive<Item>(vi.fn(async () => {}))
    toggle.reason = 'viejo'
    toggle.ask({ id: '1', is_active: true })
    expect(toggle.open).toBe(true)
    expect(toggle.target).toEqual({ id: '1', is_active: true })
    expect(toggle.reason).toBe('')
    expect(toggle.nextActive).toBe(false)
  })

  it('confirm() desactiva un activo enviando el motivo recortado y cierra', async () => {
    const action = vi.fn(async () => {})
    const toggle = useToggleActive<Item>(action)
    toggle.ask({ id: '1', is_active: true })
    toggle.reason = '  Ya no se usa  '
    await toggle.confirm()
    expect(action).toHaveBeenCalledWith({ id: '1', is_active: true }, { is_active: false, activity_reason: 'Ya no se usa' })
    expect(toggle.open).toBe(false)
  })

  it('reactiva un inactivo y un motivo vacío viaja como null', async () => {
    const action = vi.fn(async () => {})
    const toggle = useToggleActive<Item>(action)
    toggle.ask({ id: '2', is_active: false })
    expect(toggle.nextActive).toBe(true)
    await toggle.confirm()
    expect(action).toHaveBeenCalledWith({ id: '2', is_active: false }, { is_active: true, activity_reason: null })
  })

  it('si la acción falla, deja el error y el modal abierto', async () => {
    const toggle = useToggleActive<Item>(async () => {
      throw new Error('Solo se puede en borrador.')
    })
    toggle.ask({ id: '1', is_active: true })
    await toggle.confirm()
    expect(toggle.open).toBe(true)
    expect(toggle.error).toBe('Solo se puede en borrador.')
    expect(toggle.loading).toBe(false)
  })
})
