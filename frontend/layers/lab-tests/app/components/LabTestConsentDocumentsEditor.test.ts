import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiRequestError } from '~/composables/useApi'
import { fakePage } from '~/testing/fakeApi'
import { button, click, control, flushAll, hasRow, rowOf, setChecked, submitForm } from '~/testing/dom'
import LabTestConsentDocumentsEditor from './LabTestConsentDocumentsEditor.vue'

const fake = await vi.hoisted(async () => (await import('~/testing/fakeApi')).createFakeApi())
mockNuxtImport('useApi', () => () => fake.api)

enableAutoUnmount(afterEach)

const VIH_V1 = 'Consentimiento VIH (VIH) · versión 1 (retirada)'
const VIH_V2 = 'Consentimiento VIH (VIH) · versión 2'
const VIH_V3 = 'Consentimiento VIH (VIH) · versión 3 (borrador)'
const GEN_V1 = 'Genética (GEN) · versión 1 (documento inactivo)'
const OLD_V1 = 'Antiguo (OLD) · versión 1 (retirada, documento inactivo)'

const DATOS_V1 = 'Tratamiento de datos (DAT) · versión 1'

const DOCUMENTS = [
  { id: 'vih', code: 'VIH', name: 'Consentimiento VIH', is_active: true, document_type: 'consentimiento_informado' },
  { id: 'gen', code: 'GEN', name: 'Genética', is_active: false, document_type: 'consentimiento_informado' },
  { id: 'old', code: 'OLD', name: 'Antiguo', is_active: false, document_type: 'otro' },
  // El consentimiento general no se enlaza a exámenes (el backend lo rechaza con 422).
  { id: 'dat', code: 'DAT', name: 'Tratamiento de datos', is_active: true, document_type: 'tratamiento_datos' }
]

const VERSIONS: Record<string, { id: string, version_number: number, status: 'draft' | 'published' | 'retired' }[]> = {
  vih: [
    { id: 'vih1', version_number: 1, status: 'retired' },
    { id: 'vih2', version_number: 2, status: 'published' },
    { id: 'vih3', version_number: 3, status: 'draft' }
  ],
  gen: [{ id: 'gen1', version_number: 1, status: 'published' }],
  old: [{ id: 'old1', version_number: 1, status: 'retired' }],
  dat: [{ id: 'dat1', version_number: 1, status: 'published' }]
}

beforeEach(() => {
  fake.reset()
  document.body.innerHTML = ''
  fake.routes['GET /consent-documents'] = fakePage(DOCUMENTS)
  // El backend filtra por `status` (el editor pide solo las publicadas).
  for (const [documentId, versions] of Object.entries(VERSIONS)) {
    fake.routes[`GET /consent-documents/${documentId}/versions`] = (options: unknown) => fakePage(versions.filter(
      version => version.status === (options as { params?: { status?: string } }).params?.status
    ))
    for (const version of versions) {
      fake.routes[`GET /consent-document-versions/${version.id}`] = { ...version, owner: DOCUMENTS.find(d => d.id === documentId) }
    }
  }
  fake.routes['GET /lab-tests/t1/consent-documents'] = [
    // Vigente, aunque la versión ya fue retirada: se conserva.
    { id: 'L-vih1', consent_document_version_id: 'vih1', is_mandatory: false, is_active: true },
    // Quitada, de un documento inactivo: solo historial.
    { id: 'L-old1', consent_document_version_id: 'old1', is_mandatory: true, is_active: false }
  ]
  fake.routes['GET /activity'] = { items: [], total: 0, page: 1, page_size: 20 }
})

async function mountEditor() {
  const wrapper = await mountSuspended(LabTestConsentDocumentsEditor, { props: { labTestId: 't1' }, attachTo: document.body })
  await flushAll()
  const root = wrapper.element.parentElement as HTMLElement
  return { root, form: root.querySelector('form')! }
}

describe('LabTestConsentDocumentsEditor', () => {
  it('ofrece solo versiones publicadas de documentos activos y conserva la asignada retirada', async () => {
    const { root } = await mountEditor()
    expect(hasRow(root, VIH_V2)).toBe(true)
    expect(hasRow(root, VIH_V3)).toBe(false)
    expect(hasRow(root, GEN_V1)).toBe(false)
    // Catálogo: solo publicadas; las asignadas que no lo están, por su id (con su documento).
    expect(fake.requests).toHaveBeenCalledWith('GET', '/consent-documents/vih/versions', { params: { page_size: 200, status: 'published' }, cacheTtl: CATALOG_CACHE_TTL })
    expect(fake.requests).toHaveBeenCalledWith('GET', '/consent-document-versions/vih1', undefined)
    expect(fake.requests).toHaveBeenCalledWith('GET', '/consent-document-versions/old1', undefined)
    expect(fake.requests).not.toHaveBeenCalledWith('GET', '/consent-document-versions/vih2', undefined)
    const v1 = rowOf(root, VIH_V1)
    expect(control(v1, VIH_V1).checked).toBe(true)
    expect(control(v1, 'Obligatorio').checked).toBe(false)
  })

  it('no ofrece los documentos de tratamiento de datos (general) ni consulta sus versiones', async () => {
    const { root } = await mountEditor()
    expect(hasRow(root, DATOS_V1)).toBe(false)
    expect(fake.requests).not.toHaveBeenCalledWith('GET', '/consent-documents/dat/versions', expect.anything())
    // Los de examen siguen ofreciéndose.
    expect(hasRow(root, VIH_V2)).toBe(true)
  })

  it('una versión general ya asignada se sigue mostrando, marcada', async () => {
    fake.routes['GET /lab-tests/t1/consent-documents'] = [
      { id: 'L-dat1', consent_document_version_id: 'dat1', is_mandatory: true, is_active: true }
    ]
    const { root } = await mountEditor()
    expect(control(rowOf(root, DATOS_V1), DATOS_V1).checked).toBe(true)
    expect(fake.requests).toHaveBeenCalledWith('GET', '/consent-document-versions/dat1', undefined)
  })

  it('el 422 por asignar un documento general se muestra en el aviso del panel', async () => {
    fake.failures['PUT /lab-tests/t1/consent-documents'] = new ApiRequestError(
      { code: 'validation_error', message: 'No se puede asignar el consentimiento general a un examen.', details: { invalid_ids: ['dat1'] } },
      422
    )
    const { root, form } = await mountEditor()
    await setChecked(root, VIH_V2, true)
    await submitForm(form)
    expect(form.querySelector('[role="alert"]')?.textContent).toContain('consentimiento general')
  })

  it('el historial no seleccionable solo aparece con "Mostrar inactivos"', async () => {
    const { root } = await mountEditor()
    expect(hasRow(root, OLD_V1)).toBe(false)
    await setChecked(root, 'Mostrar inactivos', true)
    const old = rowOf(root, OLD_V1)
    expect(control(old, OLD_V1).disabled).toBe(true)
    expect(old.textContent).toContain('Asignación quitada')
  })

  it('"Actividad" de una fila consulta el historial con el id de esa asignación', async () => {
    const { root } = await mountEditor()
    await setChecked(root, 'Mostrar inactivos', true)
    await click(button(rowOf(root, OLD_V1), 'Actividad'))
    expect(fake.requests).toHaveBeenCalledWith('GET', '/activity', {
      params: { entity_type: 'lab_test_consent_documents', entity_id: 'L-old1', page: 1, page_size: 20 }
    })
  })

  it('el PUT envía el set completo (sin sort_order)', async () => {
    const { root, form } = await mountEditor()
    await setChecked(root, VIH_V2, true)
    await submitForm(form)
    expect(fake.bodies('PUT', '/lab-tests/t1/consent-documents')).toEqual([[
      { consent_document_version_id: 'vih1', is_mandatory: false },
      { consent_document_version_id: 'vih2', is_mandatory: true }
    ]])
    expect(root.textContent).toContain('Documentos guardados.')
  })

  it('desmarcar la versión vigente la quita del PUT', async () => {
    const { root, form } = await mountEditor()
    await setChecked(root, VIH_V1, false)
    await submitForm(form)
    expect(fake.bodies('PUT', '/lab-tests/t1/consent-documents')).toEqual([[]])
  })

  it('el 422 de versión no publicada se muestra en el aviso del formulario', async () => {
    fake.failures['PUT /lab-tests/t1/consent-documents'] = new ApiRequestError(
      { code: 'validation_error', message: 'Las siguientes versiones de documento no existen o no estan publicadas: vih2.', details: { invalid_ids: ['vih2'] } },
      422
    )
    const { root, form } = await mountEditor()
    await setChecked(root, VIH_V2, true)
    await submitForm(form)
    expect(form.querySelector('[role="alert"]')?.textContent).toContain('no estan publicadas: vih2.')
  })
})
