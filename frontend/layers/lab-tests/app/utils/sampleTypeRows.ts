import { z } from 'zod'
import type { LabTestSampleTypeInput, LabTestSampleOption } from '../types/lab-tests'
import type { LabTestAssignmentCatalogEntry } from './assignmentRows'

/**
 * Filas del formulario de tipos de muestra del examen (el recipiente: tubo
 * tapa roja…), compartidas por la pestaña "Muestras" (editar) y la sección de
 * "Nuevo examen". Reglas del backend: mínimo uno y exactamente un preferido.
 */
export const LAB_TEST_NO_SAMPLE_TYPES_MESSAGE = 'El examen debe tener al menos un tipo de muestra.'
export const LAB_TEST_PREFERRED_MESSAGE = 'Marca exactamente un tipo de muestra como preferido.'

export const labTestSampleTypeRowSchema = z.object({
  sample_type_id: z.string(),
  selected: z.boolean(),
  is_preferred: z.boolean(),
  required_volume_ml: zOptionalNumber({ min: 0 })
})

/** Regla de la lista: ≥ 1 marcado y exactamente un preferido entre ellos. */
export function checkSampleTypeRows(rows: ReadonlyArray<{ selected: boolean, is_preferred: boolean }>, ctx: z.RefinementCtx) {
  const selected = rows.filter(row => row.selected)
  if (selected.length === 0) {
    ctx.addIssue({ code: z.ZodIssueCode.custom, message: LAB_TEST_NO_SAMPLE_TYPES_MESSAGE })
  } else if (selected.filter(row => row.is_preferred).length !== 1) {
    ctx.addIssue({ code: z.ZodIssueCode.custom, message: LAB_TEST_PREFERRED_MESSAGE })
  }
}

export const labTestSampleTypeRowsSchema = z.array(labTestSampleTypeRowSchema).superRefine(checkSampleTypeRows)

export type LabTestSampleTypeRowValues = z.input<typeof labTestSampleTypeRowSchema>

export function emptySampleTypeRow(id: string): LabTestSampleTypeRowValues {
  return { sample_type_id: id, selected: false, is_preferred: false, required_volume_ml: '' }
}

/** Preferido es exclusivo: deja `is_preferred` solo en la fila `index`. */
export function preferSampleTypeRow<R extends { is_preferred: boolean }>(rows: readonly R[], index: number): R[] {
  return rows.map((row, i) => (i === index ? row : { ...row, is_preferred: false }))
}

/** Body (POST del examen / PUT de sample-types): marcados, `sort_order` = posición. */
export function labTestSampleTypesPayload(rows: ReadonlyArray<z.output<typeof labTestSampleTypeRowSchema>>): LabTestSampleTypeInput[] {
  return labTestOrderedAssignmentPayload(rows).map(({ sample_type_id, is_preferred, required_volume_ml, sort_order }) => ({
    sample_type_id,
    is_preferred,
    required_volume_ml,
    sort_order
  }))
}

/** Catálogo de tipos (todos, para poder nombrar inactivos); ofrecible = tipo y muestra activos. */
export function sampleTypeCatalogEntries(samples: readonly LabTestSampleOption[]): LabTestAssignmentCatalogEntry[] {
  return samples.flatMap(sample => sample.types.map(type => ({
    id: type.id,
    label: `${type.name} (${type.code} · ${sample.name})`,
    isActive: type.is_active && sample.is_active
  })))
}
