import { describe, expect, it } from 'vitest'
import {
  buildLabTestAssignmentRows,
  labTestAssignmentPayload,
  labTestOrderedAssignmentPayload,
  visibleLabTestAssignmentRows
} from './assignmentRows'

const catalog = [
  { id: 'a', label: 'A', isActive: true },
  { id: 'b', label: 'B', isActive: true },
  { id: 'c', label: 'C', isActive: false },
  { id: 'd', label: 'D', isActive: true, indent: true }
]

describe('buildLabTestAssignmentRows', () => {
  it('primero las asignaciones activas en su orden, luego el catálogo activo sin asignar', () => {
    const rows = buildLabTestAssignmentRows(
      [
        { id: 'b', isActive: true, sortOrder: 2 },
        { id: 'a', isActive: true, sortOrder: 1 }
      ],
      catalog
    )
    expect(rows.map(r => [r.id, r.assigned, r.selectable])).toEqual([
      ['a', true, true],
      ['b', true, true],
      ['d', false, true]
    ])
    expect(rows.map(r => r.index)).toEqual([0, 1, 2])
    expect(rows[2]!.indent).toBe(true)
  })

  it('una asignación activa a un elemento ya desactivado se conserva marcada como inactiva', () => {
    const rows = buildLabTestAssignmentRows([{ id: 'c', isActive: true, sortOrder: 1 }], catalog)
    expect(rows[0]).toMatchObject({ id: 'c', label: 'C', assigned: true, selectable: true, elementInactive: true })
    // El elemento inactivo no se ofrece para agregar.
    expect(rows.filter(r => r.id === 'c')).toHaveLength(1)
  })

  it('un elemento desconocido asignado usa la etiqueta de respaldo y queda como inactivo', () => {
    const rows = buildLabTestAssignmentRows([{ id: 'x', isActive: true, sortOrder: 1, fallbackLabel: 'Glucosa' }], catalog)
    expect(rows[0]).toMatchObject({ id: 'x', label: 'Glucosa', assigned: true, elementInactive: true })
  })

  it('una asignación quitada (inactiva) de un elemento activo se ofrece de nuevo y se marca', () => {
    const rows = buildLabTestAssignmentRows([{ id: 'a', isActive: false, sortOrder: 1 }], catalog)
    expect(rows.find(r => r.id === 'a')).toMatchObject({ assigned: false, selectable: true, linkInactive: true })
  })

  it('una asignación quitada de un elemento inactivo queda solo como historial (no seleccionable)', () => {
    const rows = buildLabTestAssignmentRows([{ id: 'c', isActive: false, sortOrder: 1 }], catalog)
    expect(rows.find(r => r.id === 'c')).toMatchObject({
      assigned: false,
      selectable: false,
      linkInactive: true,
      elementInactive: true
    })
  })
})

describe('linkId (historial de la asignación)', () => {
  it('cada fila lleva el id de su asignación: la vigente, la quitada o null si nunca se asignó', () => {
    const rows = buildLabTestAssignmentRows(
      [
        { id: 'a', linkId: 'L-a', isActive: true, sortOrder: 1 },
        { id: 'b', linkId: 'L-b', isActive: false, sortOrder: 2 },
        { id: 'c', linkId: 'L-c', isActive: false, sortOrder: 3 }
      ],
      catalog
    )
    const byId = Object.fromEntries(rows.map(r => [r.id, r.linkId]))
    expect(byId).toEqual({ a: 'L-a', b: 'L-b', d: null, c: 'L-c' })
  })
})

describe('visibleLabTestAssignmentRows', () => {
  const rows = buildLabTestAssignmentRows([{ id: 'c', isActive: false, sortOrder: 1 }], catalog)

  it('oculta el historial no seleccionable salvo con "Mostrar inactivos"', () => {
    expect(visibleLabTestAssignmentRows(rows, false).map(r => r.id)).toEqual(['a', 'b', 'd'])
    expect(visibleLabTestAssignmentRows(rows, true).map(r => r.id)).toEqual(['a', 'b', 'd', 'c'])
  })
})

describe('payload del PUT de asignaciones', () => {
  const rows = [
    { item_id: 'a', selected: true, is_mandatory: false },
    { item_id: 'b', selected: false, is_mandatory: true },
    { item_id: 'c', selected: true, is_mandatory: true }
  ]

  it('labTestAssignmentPayload: solo las filas marcadas, sin `selected`', () => {
    expect(labTestAssignmentPayload(rows)).toEqual([
      { item_id: 'a', is_mandatory: false },
      { item_id: 'c', is_mandatory: true }
    ])
  })

  it('labTestOrderedAssignmentPayload: además, sort_order = posición entre las marcadas (desde 1)', () => {
    expect(labTestOrderedAssignmentPayload(rows)).toEqual([
      { item_id: 'a', is_mandatory: false, sort_order: 1 },
      { item_id: 'c', is_mandatory: true, sort_order: 2 }
    ])
  })

  it('sin filas marcadas devuelve un set vacío (el PUT quita todo)', () => {
    expect(labTestOrderedAssignmentPayload(rows.map(row => ({ ...row, selected: false })))).toEqual([])
  })
})
