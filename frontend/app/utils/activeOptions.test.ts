import { describe, expect, it } from 'vitest'
import { activeSelectOptions } from './activeOptions'

const items = [
  { id: 'a', name: 'Activa', is_active: true },
  { id: 'b', name: 'Inactiva', is_active: false },
  { id: 'c', name: 'Otra', is_active: true }
]
const label = (item: { name: string }) => item.name

describe('activeSelectOptions', () => {
  it('ofrece solo los activos, en su orden', () => {
    expect(activeSelectOptions(items, label)).toEqual([
      { value: 'a', label: 'Activa' },
      { value: 'c', label: 'Otra' }
    ])
  })

  it('incluye el valor ya seleccionado aunque esté inactivo, marcado "(inactivo)"', () => {
    expect(activeSelectOptions(items, label, 'b')).toEqual([
      { value: 'a', label: 'Activa' },
      { value: 'b', label: 'Inactiva (inactivo)' },
      { value: 'c', label: 'Otra' }
    ])
  })

  it('acepta varios valores actuales y ignora vacíos', () => {
    expect(activeSelectOptions(items, label, ['b', null, '']).map(o => o.value)).toEqual(['a', 'b', 'c'])
  })

  it('un valor actual activo no cambia su etiqueta', () => {
    expect(activeSelectOptions(items, label, 'a')[0]).toEqual({ value: 'a', label: 'Activa' })
  })
})
