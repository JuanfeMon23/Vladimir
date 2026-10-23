import { describe, expect, it } from 'vitest'
import { apiError as backendError } from '~/testing/apiError'
import {
  consentDocumentFilename,
  consentFileApiError,
  describeConsentPublishErrors,
  isGeneralConsent,
  isGeneralDocumentConflict
} from './consentDocuments'

function apiError(code: string, message: string, details: unknown, status: number) {
  return backendError({ code, message, details }, status)
}

describe('consentFileApiError', () => {
  it.each([
    ['empty', 'El archivo está vacío.'],
    ['too_large', 'El archivo supera los 5 MB.'],
    ['invalid_base64', 'El archivo no se pudo leer correctamente.'],
    ['not_pdf', 'El archivo no es un PDF válido.']
  ])('traduce el reason %s del campo file_base64', (reason, message) => {
    const err = apiError('validation_error', 'texto del backend', { field: 'file_base64', reason }, 422)
    expect(consentFileApiError(err)).toBe(message)
  })

  it('usa el mensaje del backend con un reason desconocido', () => {
    const err = apiError('validation_error', 'texto del backend', { field: 'file_base64', reason: 'nuevo' }, 422)
    expect(consentFileApiError(err)).toBe('texto del backend')
  })

  it('devuelve null para errores que no son del archivo', () => {
    expect(consentFileApiError(apiError('validation_error', 'x', { field: 'content' }, 422))).toBeNull()
    expect(consentFileApiError(apiError('not_found', 'x', null, 404))).toBeNull()
    expect(consentFileApiError(new Error('red'))).toBeNull()
  })
})

describe('describeConsentPublishErrors', () => {
  it('describe el archivo faltante en español', () => {
    expect(describeConsentPublishErrors({ missing_fields: ['file_base64'] })).toEqual(['Adjunta el PDF antes de publicar.'])
  })

  it('describe otros campos faltantes y conserva los desconocidos', () => {
    expect(describeConsentPublishErrors({ missing_fields: ['content', 'signer', 'otro'] })).toEqual([
      'Falta el contenido.',
      'Falta el firmante.',
      'Falta: otro.'
    ])
  })

  it('devuelve lista vacía sin missing_fields', () => {
    expect(describeConsentPublishErrors(null)).toEqual([])
    expect(describeConsentPublishErrors({ otra: 1 })).toEqual([])
    expect(describeConsentPublishErrors({ missing_fields: [] })).toEqual([])
  })
})

describe('isGeneralDocumentConflict', () => {
  it('reconoce el 409 de segundo general activo (details con code e id)', () => {
    const err = apiError('conflict', 'Ya existe un documento activo…', { code: 'CONSENT_DATOS', id: 'abc' }, 409)
    expect(isGeneralDocumentConflict(err)).toBe(true)
  })

  it('no confunde el código duplicado (details solo con code) ni otros errores', () => {
    expect(isGeneralDocumentConflict(apiError('conflict', 'dup', { code: 'X' }, 409))).toBe(false)
    expect(isGeneralDocumentConflict(apiError('validation_error', 'x', { code: 'X', id: '1' }, 422))).toBe(false)
    expect(isGeneralDocumentConflict(new Error('x'))).toBe(false)
  })
})

describe('isGeneralConsent', () => {
  it('es el documento de tratamiento de datos', () => {
    expect(isGeneralConsent({ document_type: 'tratamiento_datos' })).toBe(true)
    expect(isGeneralConsent({ document_type: 'consentimiento_informado' })).toBe(false)
    expect(isGeneralConsent({ document_type: 'otro' })).toBe(false)
  })
})

describe('consentDocumentFilename', () => {
  it('arma <codigo>-v<N>.pdf', () => {
    expect(consentDocumentFilename('CONSENT_VIH', 2)).toBe('CONSENT_VIH-v2.pdf')
  })

  it('sanea caracteres no válidos en nombres de archivo', () => {
    expect(consentDocumentFilename('A/B C', 1)).toBe('A-B-C-v1.pdf')
  })
})
