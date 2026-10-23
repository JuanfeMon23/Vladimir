import { describe, expect, it } from 'vitest'
import { ACTIVITY_ACTION_LABELS, withActivityReason } from '#andromeda/utils/activity'
import { formatDateTime } from '#andromeda/utils/formatDateTime'

describe('withActivityReason', () => {
  const values = { name: 'Hemoglobina', is_active: false, activity_reason: 'Ya no se procesa' }

  it('al crear (sin estado inicial) no envía el motivo', () => {
    expect(withActivityReason(values, undefined)).toEqual({ name: 'Hemoglobina', is_active: false })
  })

  it('al editar sin cambiar is_active no envía el motivo', () => {
    expect(withActivityReason(values, false)).toEqual({ name: 'Hemoglobina', is_active: false })
  })

  it('al editar cambiando is_active envía el motivo', () => {
    expect(withActivityReason(values, true)).toEqual(values)
  })

  it('motivo vacío (null) viaja como null cuando el estado cambia', () => {
    expect(withActivityReason({ is_active: true, activity_reason: null }, false)).toEqual({
      is_active: true,
      activity_reason: null
    })
  })
})

describe('formatDateTime', () => {
  it('formatea una fecha ISO con fecha y hora locales', () => {
    const text = formatDateTime('2026-10-02T15:30:00Z')
    expect(text).toContain('2026')
    expect(text).toMatch(/\d{1,2}:\d{2}/)
  })

  it('devuelve el texto original si no es una fecha válida', () => {
    expect(formatDateTime('no-es-fecha')).toBe('no-es-fecha')
  })
})

describe('ACTIVITY_ACTION_LABELS', () => {
  it('traduce las acciones del backend', () => {
    expect(ACTIVITY_ACTION_LABELS).toEqual({ activated: 'Activado', deactivated: 'Desactivado' })
  })
})
