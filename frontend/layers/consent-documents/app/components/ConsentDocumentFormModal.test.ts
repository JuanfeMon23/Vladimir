import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { apiError } from '~/testing/apiError'
import { CATALOG_FIXTURES, fakeCatalogs } from '~/testing/catalogs'
import { fakePage } from '~/testing/fakeApi'
import { ALL_CONSENT_DOCUMENTS_TAGS } from '~/testing/session'
import { signInWith } from '#leo-client/testing/session'
import { button, click, control, fieldError, flushAll, optionLabels, setChecked, setValue, submitForm } from '#andromeda/testing/dom'
import type { ConsentDocumentRead } from '../types/consent-documents'
import ConsentDocumentFormModal from './ConsentDocumentFormModal.vue'

const fake = await vi.hoisted(async () => (await import('~/testing/fakeApi')).createFakeApi())
mockNuxtImport('useLeoAppApi', () => () => fake.api)

enableAutoUnmount(afterEach)

const GENERAL_CONFLICT = 'Ya existe un documento activo de tratamiento de datos personales (CONSENT_DATOS). Desactívalo antes de activar otro.'

function entity(overrides: Partial<ConsentDocumentRead> = {}): ConsentDocumentRead {
  return {
    id: 'd1',
    code: 'CONSENT_VIH',
    name: 'Consentimiento VIH',
    description: null,
    document_type: 'consentimiento_informado',
    is_active: true,
    created_at: '2026-10-09T00:00:00Z',
    updated_at: '2026-10-09T00:00:00Z',
    ...overrides
  }
}

beforeEach(() => {
  signInWith([...ALL_CONSENT_DOCUMENTS_TAGS, MODULE_VIEW.catalogs.tag])
  fake.reset()
  fakeCatalogs(fake, ['consent-document-types', 'consent-signers'])
  document.body.innerHTML = ''
  fake.routes['GET /consent-documents/d1/versions'] = fakePage([])
  fake.routes['GET /activity'] = fakePage([])
})

async function mountModal(doc: ConsentDocumentRead | null) {
  await mountSuspended(ConsentDocumentFormModal, { props: { open: true, entity: doc }, attachTo: document.body })
  await flushAll()
  const dialog = document.body.querySelector<HTMLElement>('[role="dialog"]')!
  return { dialog, form: dialog.querySelector('form')! }
}

describe('ConsentDocumentFormModal', () => {
  it('ofrece los tipos con etiquetas legibles y la ayuda del consentimiento general', async () => {
    const { dialog } = await mountModal(null)
    expect(optionLabels(control<HTMLSelectElement>(dialog, 'Tipo de documento'))).toEqual([
      'Seleccionar tipo',
      'Consentimiento informado de examen',
      'Tratamiento de datos (general)',
      'Otro'
    ])
    expect(dialog.textContent).toContain('El consentimiento general se firma antes de cualquier examen; solo puede haber uno activo.')
  })

  it('marca el general vigente con un badge distintivo (y no los demás)', async () => {
    const general = await mountModal(entity({ document_type: 'tratamiento_datos', code: 'CONSENT_DATOS' }))
    expect(general.dialog.textContent).toContain('Consentimiento general vigente')
    document.body.innerHTML = ''
    const inactive = await mountModal(entity({ document_type: 'tratamiento_datos', is_active: false }))
    expect(inactive.dialog.textContent).not.toContain('Consentimiento general vigente')
    document.body.innerHTML = ''
    const exam = await mountModal(entity())
    expect(exam.dialog.textContent).not.toContain('Consentimiento general vigente')
  })

  it('el 409 de segundo general activo se muestra en Tipo de documento y Activo, no en Código', async () => {
    fake.failures['POST /consent-documents'] = apiError(
      { code: 'conflict', message: GENERAL_CONFLICT, details: { code: 'CONSENT_DATOS', id: 'd0' } },
      409
    )
    const { dialog, form } = await mountModal(null)
    await setValue(control(dialog, 'Código'), 'NUEVO')
    await setValue(control(dialog, 'Nombre'), 'Otro general')
    await setValue(control(dialog, 'Tipo de documento'), 'tratamiento_datos')
    await submitForm(form)
    expect(fieldError(dialog, 'Tipo de documento')).toBe(GENERAL_CONFLICT)
    expect(dialog.textContent).toContain(GENERAL_CONFLICT)
    expect(fieldError(dialog, 'Código')).toBeNull()
    // El modal sigue abierto para corregir.
    expect(document.body.querySelector('[role="dialog"]')).not.toBeNull()
  })

  it('el 409 al reactivar un general se muestra junto a Activo', async () => {
    fake.failures['PATCH /consent-documents/d1'] = apiError(
      { code: 'conflict', message: GENERAL_CONFLICT, details: { code: 'CONSENT_DATOS', id: 'd0' } },
      409
    )
    const { dialog, form } = await mountModal(entity({ document_type: 'tratamiento_datos', is_active: false }))
    await setChecked(dialog, 'Activo', true)
    await submitForm(form)
    expect(dialog.textContent).toContain(GENERAL_CONFLICT)
    expect(fieldError(dialog, 'Código')).toBeNull()
  })

  it('un código duplicado (409 sin id) sigue yendo al campo Código', async () => {
    fake.failures['POST /consent-documents'] = apiError(
      { code: 'conflict', message: 'Ya existe un documento con el código NUEVO.', details: { code: 'NUEVO' } },
      409
    )
    const { dialog, form } = await mountModal(null)
    await setValue(control(dialog, 'Código'), 'NUEVO')
    await setValue(control(dialog, 'Nombre'), 'X')
    await setValue(control(dialog, 'Tipo de documento'), 'otro')
    await submitForm(form)
    expect(fieldError(dialog, 'Código')).toBe('Ya existe un documento con el código NUEVO.')
  })

  it('los tipos salen del catálogo de la API: un tipo nuevo aparece sin tocar el código', async () => {
    fake.routes['GET /catalogs/consent-document-types'] = [
      { id: 'x', code: 'autorizacion_imagen', name: 'Autorización de imagen', sort_order: 0, is_active: true, created_at: '', updated_at: '' }
    ]
    const { dialog } = await mountModal(null)
    expect(optionLabels(control<HTMLSelectElement>(dialog, 'Tipo de documento'))).toEqual(['Seleccionar tipo', 'Autorización de imagen'])
  })

  it('un tipo inactivo ya guardado se sigue mostrando, marcado "(inactivo)"', async () => {
    fake.routes['GET /catalogs/consent-document-types'] = [
      ...CATALOG_FIXTURES['consent-document-types'],
      { id: 'v', code: 'viejo', name: 'Tipo viejo', sort_order: 9, is_active: false, created_at: '', updated_at: '' }
    ]
    const { dialog } = await mountModal(entity({ document_type: 'viejo' }))
    const select = control<HTMLSelectElement>(dialog, 'Tipo de documento')
    expect(optionLabels(select)).toContain('Tipo viejo (inactivo)')
    expect(select.value).toBe('viejo')
  })

  it.each([
    ['invalid_reference', 'El tipo de documento «raro» no existe.'],
    ['inactive_reference', 'El tipo de documento «otro» está inactivo.']
  ])('el 422 %s se muestra en Tipo de documento', async (code, message) => {
    fake.failures['POST /consent-documents'] = apiError({ code, message, details: { document_type: 'otro' } }, 422)
    const { dialog, form } = await mountModal(null)
    await setValue(control(dialog, 'Código'), 'NUEVO')
    await setValue(control(dialog, 'Nombre'), 'Nuevo')
    await setValue(control(dialog, 'Tipo de documento'), 'otro')
    await submitForm(form)
    expect(fieldError(dialog, 'Tipo de documento')).toBe(message)
    expect(fieldError(dialog, 'Código')).toBeNull()
  })

  it('la primera versión se crea con el primer firmante activo del catálogo', async () => {
    fake.routes['GET /catalogs/consent-signers'] = [
      { id: 'a', code: 'tutor', name: 'Tutor', sort_order: 0, is_active: false, created_at: '', updated_at: '' },
      { id: 'b', code: 'representante', name: 'Representante', sort_order: 1, is_active: true, created_at: '', updated_at: '' }
    ]
    const { dialog } = await mountModal(entity())
    await click(button(dialog, 'Nueva versión'))
    await flushAll()
    expect(fake.bodies('POST', '/consent-documents/d1/versions')[0]).toMatchObject({ signer: 'representante' })
  })
})
