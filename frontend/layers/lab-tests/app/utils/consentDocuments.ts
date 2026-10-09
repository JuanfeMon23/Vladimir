import type { LabTestConsentDocumentOption } from '../types/lab-tests'

/**
 * Tipo del consentimiento general de tratamiento de datos: se firma antes de
 * cualquier examen y NO se enlaza a exámenes (el backend responde 422).
 */
export const LAB_TEST_GENERAL_CONSENT_TYPE = 'tratamiento_datos'

/** Documentos que se pueden asignar a un examen (todos menos el consentimiento general). */
export function examConsentDocuments<T extends Pick<LabTestConsentDocumentOption, 'document_type'>>(documents: T[]): T[] {
  return documents.filter(document => document.document_type !== LAB_TEST_GENERAL_CONSENT_TYPE)
}
