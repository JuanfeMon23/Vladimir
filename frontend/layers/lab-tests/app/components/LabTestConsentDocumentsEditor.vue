<script setup lang="ts">
/**
 * Pestaña "Documentos" del examen: las versiones publicadas
 * (`?status=published`) de los documentos a firmar activos, más las ya
 * asignadas aunque ya no lo estén (cada una pedida por su id con su
 * documento, `GET /consent-document-versions/{id}`), marcadas; el consentimiento
 * general (`tratamiento_datos`) no se ofrece, pero uno ya asignado se muestra;
 * con un checkbox por fila y "obligatorio". Guarda con
 * `PUT /lab-tests/{id}/consent-documents` (set completo; el backend quita lo
 * que falta y rechaza con 422 agregar algo no publicado o inactivo, que se
 * muestra en el aviso del formulario).
 */
import { z } from 'zod'
import type { LabTestCatalogOption, LabTestConsentDocumentInput, LabTestVersionOption } from '../types/lab-tests'
import { examConsentDocuments } from '../utils/consentDocuments'
import type { LabTestAssignmentCatalogEntry, LabTestAssignmentRow } from '../utils/assignmentRows'

const props = defineProps<{ labTestId: string }>()

const labTestsApi = useLabTests()
/** Sin el `view` del módulo del catálogo no se pide nada (el panel avisa el permiso que falta). */
const canConsult = useCan(MODULE_VIEW.consentDocuments.tag)

const rowSchema = z.object({
  consent_document_version_id: z.string(),
  selected: z.boolean(),
  is_mandatory: z.boolean()
})
const schema = z.object({ rows: z.array(rowSchema) })
type RowValues = z.input<typeof rowSchema>

const form = useZodForm(schema, { initialValues: { rows: [] } })
const { submit, isSubmitting, formError, reset } = form

function emptyRow(id: string): RowValues {
  return { consent_document_version_id: id, selected: false, is_mandatory: true }
}

/** Fila del catálogo de una versión: asignable solo si está publicada y su documento activo. */
function toEntry(document: LabTestCatalogOption, version: LabTestVersionOption): LabTestAssignmentCatalogEntry {
  const notes = [
    version.status === 'published' ? '' : VERSION_STATUS_LABELS[version.status].toLowerCase(),
    document.is_active ? '' : 'documento inactivo'
  ].filter(Boolean)
  return {
    id: version.id,
    label: `${document.name} (${document.code}) · versión ${version.version_number}${notes.length ? ` (${notes.join(', ')})` : ''}`,
    isActive: document.is_active && version.status === 'published'
  }
}

const catalog = useLabTestAssignmentCatalog<LabTestAssignmentRow>(async () => {
  const [assigned, documents] = await Promise.all([
    labTestsApi.getConsentDocuments(props.labTestId, { include_inactive: true }),
    labTestsApi.listConsentDocumentOptions()
  ])
  // El consentimiento general (tratamiento_datos) no se enlaza a exámenes: no se ofrece.
  const versionsByDocument = await Promise.all(
    examConsentDocuments(documents).map(async document => ({ document, versions: await labTestsApi.listPublishedConsentDocumentVersions(document.id) }))
  )

  // Catálogo: versiones publicadas; se puede agregar solo si su documento está activo.
  const entries: LabTestAssignmentCatalogEntry[] = versionsByDocument.flatMap(({ document, versions }) =>
    [...versions].sort((a, b) => b.version_number - a.version_number).map(version => toEntry(document, version))
  )
  // Asignadas (vigentes o quitadas) que ya no están publicadas: por su id, con su documento.
  const known = new Set(entries.map(entry => entry.id))
  const missing = [...new Set(assigned.map(item => item.consent_document_version_id))].filter(id => !known.has(id))
  const extra = await Promise.all(missing.map(id => labTestsApi.getConsentDocumentVersion(id)))
  entries.push(...extra.map(version => toEntry(version.owner, version)))

  const mandatoryById = new Map(assigned.filter(item => item.is_active).map(item => [item.consent_document_version_id, item.is_mandatory]))
  const rows = buildLabTestAssignmentRows(
    assigned.map((item, index) => ({ id: item.consent_document_version_id, linkId: item.id, isActive: item.is_active, sortOrder: index })),
    entries
  )
  reset({
    rows: rows.map(row => row.assigned
      ? { consent_document_version_id: row.id, selected: true, is_mandatory: mandatoryById.get(row.id) ?? true }
      : emptyRow(row.id))
  })
  return rows
}, 'No se pudo cargar el catálogo de documentos a firmar.', () => canConsult.value)

const { isSelected, onToggle } = useLabTestAssignmentRows(form, emptyRow)

const savedMessage = ref<string | null>(null)

const onSubmit = submit(async ({ rows }) => {
  savedMessage.value = null
  const items: LabTestConsentDocumentInput[] = labTestAssignmentPayload(rows)
  await labTestsApi.putConsentDocuments(props.labTestId, items)
  savedMessage.value = 'Documentos guardados.'
})
</script>

<template>
  <LabTestAssignmentPanel
    :catalog-module="MODULE_VIEW.consentDocuments"
    :save-tag="LAB_TESTS_TAGS.setConsentDocuments"
    activity-entity-type="lab_test_consent_documents"
    title="Documentos a firmar"
    description="Marca las versiones publicadas de los documentos que el paciente debe firmar para este examen."
    :items="catalog.rows"
    :loading="catalog.loading"
    :load-error="catalog.loadError"
    :form-error="formError"
    :saved-message="savedMessage"
    :submitting="isSubmitting"
    submit-label="Guardar documentos"
    empty-message="No hay versiones publicadas de documentos a firmar."
    @submit="onSubmit"
  >
    <template #default="{ item: row }">
      <div class="flex flex-wrap items-center justify-between gap-x-6 gap-y-2">
        <UiFormField :name="`rows[${row.index}].selected`">
          <UiCheckbox :label="row.label" :disabled="!row.selectable" @update:model-value="onToggle(row, $event)" />
        </UiFormField>
        <UiFormField v-show="isSelected(row)" :name="`rows[${row.index}].is_mandatory`">
          <UiCheckbox label="Obligatorio" />
        </UiFormField>
      </div>
    </template>
  </LabTestAssignmentPanel>
</template>
