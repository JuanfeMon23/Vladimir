import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiRequestError } from '~/composables/useApi'
import { fakePage } from '~/testing/fakeApi'
import { control, fieldError, flushAll, optionLabels, setChecked, setValue, submitForm } from '~/testing/dom'
import type { ConsentDocumentRead } from '../types/consent-documents'
import ConsentDocumentFormModal from './ConsentDocumentFormModal.vue'

const fake = await vi.hoisted(async () => (await import('~/testing/fakeApi')).createFakeApi())
mockNuxtImport('useApi', () => () => fake.api)

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
  fake.reset()
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
    fake.failures['POST /consent-documents'] = new ApiRequestError(
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
    fake.failures['PATCH /consent-documents/d1'] = new ApiRequestError(
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
    fake.failures['POST /consent-documents'] = new ApiRequestError(
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
})
