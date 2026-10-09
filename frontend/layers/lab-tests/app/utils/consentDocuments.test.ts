import { describe, expect, it } from 'vitest'
import { examConsentDocuments } from './consentDocuments'

describe('examConsentDocuments', () => {
  it('excluye el consentimiento general y conserva los de examen y "otro"', () => {
    const documents = [
      { id: 'a', document_type: 'consentimiento_informado' },
      { id: 'b', document_type: 'tratamiento_datos' },
      { id: 'c', document_type: 'otro' }
    ]
    expect(examConsentDocuments(documents).map(d => d.id)).toEqual(['a', 'c'])
  })

  it('lista vacía -> vacía', () => {
    expect(examConsentDocuments([])).toEqual([])
  })
})
