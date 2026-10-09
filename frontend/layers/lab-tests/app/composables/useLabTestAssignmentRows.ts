import type { LabTestAssignmentRow } from '../utils/assignmentRows'

/** Lo que usa del `useZodForm` de una pestaña de asignaciones (`{ rows: R[] }`). */
export interface LabTestAssignmentRowsForm<R> {
  values: { rows?: R[] }
  setFieldValue: (field: 'rows', value: R[], shouldValidate?: boolean) => void
}

/**
 * Acciones sobre las filas del formulario de una pestaña de asignaciones del
 * examen (precondiciones, tipos de muestra, documentos):
 * - `isSelected(row)`: la fila está marcada (muestra sus campos).
 * - `onToggle(row, checked)`: al desmarcar, la fila vuelve a `emptyRow(id)`
 *   (sin overrides ni errores ocultos).
 * - `updateRows(fn)`: reemplaza todas las filas sin validar (p. ej. el
 *   "preferido" exclusivo de los tipos de muestra).
 */
export function useLabTestAssignmentRows<R extends { selected: boolean }>(
  form: LabTestAssignmentRowsForm<R>,
  emptyRow: (id: string) => R
) {
  const isSelected = (row: LabTestAssignmentRow) => Boolean(form.values.rows?.[row.index]?.selected)

  function updateRows(fn: (rows: R[]) => R[]) {
    form.setFieldValue('rows', fn(form.values.rows ?? []), false)
  }

  function onToggle(row: LabTestAssignmentRow, checked: boolean) {
    if (checked) return
    updateRows(rows => rows.map((current, index) => (index === row.index ? emptyRow(row.id) : current)))
  }

  return { isSelected, onToggle, updateRows }
}
