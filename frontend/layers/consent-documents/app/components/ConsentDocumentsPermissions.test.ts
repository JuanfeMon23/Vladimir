import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import DefaultLayout from '~/layouts/default.vue'
import { button, control, flushAll, setChecked, setValue } from '#andromeda/testing/dom'
import { fakePage } from '~/testing/fakeApi'
import { ALL_CONSENT_DOCUMENTS_TAGS } from '~/testing/session'
import { signInWith } from '#leo-client/testing/session'
import type { ConsentDocumentRead, ConsentDocumentVersionRead } from '../types/consent-documents'
import ConsentDocumentFormModal from './ConsentDocumentFormModal.vue'
import ConsentDocumentsPage from '../pages/consent-documents/index.vue'
import VersionEditorPage from '../pages/consent-documents/[id]/versions/[versionId].vue'

const fake = await vi.hoisted(async () => (await import('~/testing/fakeApi')).createFakeApi())
mockNuxtImport('useLeoAppApi', () => () => fake.api)

enableAutoUnmount(afterEach)

const DOC: ConsentDocumentRead = {
  id: 'd1', code: 'CONSENT_VIH', name: 'Consentimiento VIH', document_type: 'consentimiento_informado',
  description: null, is_active: true, created_at: '2026-10-01T00:00:00Z', updated_at: '2026-10-01T00:00:00Z'
}

function version(overrides: Partial<ConsentDocumentVersionRead> = {}): ConsentDocumentVersionRead {
  return {
    id: 'v1', consent_document_id: 'd1', version_number: 1, status: 'draft', published_at: null, change_notes: null,
    content: '# Texto', signer: 'paciente', has_file: true, file_content_type: 'application/pdf',
    file_sha256: 'a'.repeat(64), file_size_bytes: 2048,
    created_at: '2026-10-01T00:00:00Z', updated_at: '2026-10-01T00:00:00Z',
    ...overrides
  }
}

const PREFIX = 'vladimir.consent-documents.'
const VIEW = `${PREFIX}view`
const EDIT = `${PREFIX}edit`
const STATUS = `${PREFIX}change-status`
const CREATE_VERSION = `${PREFIX}create-version`
const EDIT_VERSION = `${PREFIX}edit-version`
const PUBLISH = `${PREFIX}publish-version`
const RETIRE = `${PREFIX}retire-version`

beforeEach(() => {
  fake.reset()
  invalidateCaches()
  clearNuxtData()
  document.body.innerHTML = ''
  fake.routes['GET /consent-documents'] = fakePage([DOC])
  fake.routes['GET /consent-documents/d1'] = DOC
})

const patches = () => fake.requests.mock.calls.filter(([method]) => method === 'PATCH')
async function submit(form: HTMLFormElement) {
  form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
  await flushAll()
}

async function mountPage(tags: string[]) {
  signInWith(tags)
  const wrapper = await mountSuspended(ConsentDocumentsPage)
  await flushAll()
  return wrapper
}

async function mountModal(tags: string[], versions: ConsentDocumentVersionRead[] = []) {
  fake.routes['GET /consent-documents/d1/versions'] = fakePage(versions)
  signInWith(tags)
  await mountSuspended(ConsentDocumentFormModal, { props: { open: true, entity: DOC }, attachTo: document.body })
  await flushAll()
  const dialog = document.body.querySelector<HTMLElement>('[role="dialog"]')!
  return { dialog, form: dialog.querySelector('form')! }
}

const labels = (root: ParentNode) => [...root.querySelectorAll('a, button')].map(el => el.textContent?.trim())

describe('ruta y menú de consent-documents', () => {
  it('las páginas (listado y editor) exigen el tag view', () => {
    const meta = (path: string) => (useRouter().resolve(path).meta as { leo?: { tag?: string } }).leo?.tag
    expect(meta('/consent-documents')).toBe(VIEW)
    expect(meta('/consent-documents/d1/versions/v1')).toBe(VIEW)
  })

  it('el ítem "Documentos a firmar" aparece con view y no sin él', async () => {
    signInWith([VIEW])
    const withView = await mountSuspended(DefaultLayout)
    expect(withView.findAll('a').find(a => a.text() === 'Documentos a firmar')?.attributes('href')).toBe('/consent-documents')

    signInWith([PUBLISH])
    expect((await mountSuspended(DefaultLayout)).findAll('a').map(a => a.text())).not.toContain('Documentos a firmar')
  })
})

describe('listado y datos del documento', () => {
  it('"Nuevo documento" exige create', async () => {
    expect((await mountPage([VIEW])).text()).not.toContain('Nuevo documento')
    expect((await mountPage([VIEW, `${PREFIX}create`])).text()).toContain('Nuevo documento')
  })

  it('solo con view la acción es "Ver"; con edit o permisos de versión, "Ver / Editar"', async () => {
    expect((await mountPage([VIEW])).findAll('button').map(b => b.text())).toContain('Ver')
    expect((await mountPage([VIEW, EDIT])).findAll('button').map(b => b.text())).toContain('Ver / Editar')
    expect((await mountPage([VIEW, RETIRE])).findAll('button').map(b => b.text())).toContain('Ver / Editar')
  })

  it('con solo view el modal es de lectura (campos bloqueados, "Cerrar", sin "Activo")', async () => {
    const { dialog } = await mountModal([VIEW])
    expect(dialog.textContent).not.toContain('Guardar cambios')
    expect(labels(dialog)).not.toContain('Nueva versión')
    expect(() => button(dialog, 'Cerrar')).not.toThrow()
    expect(control(dialog, 'Nombre').disabled).toBe(true)
    expect(() => control(dialog, 'Activo')).toThrow()
  })

  it('con edit el PATCH lleva los datos y no is_active', async () => {
    const { dialog, form } = await mountModal([VIEW, EDIT])
    await setValue(control(dialog, 'Nombre'), 'Consentimiento nuevo')
    await submit(form)
    const [, path, body] = patches()[0]!
    expect(path).toBe('/consent-documents/d1')
    expect(body).toMatchObject({ name: 'Consentimiento nuevo', code: 'CONSENT_VIH' })
    expect(body).not.toHaveProperty('is_active')
  })

  it('con solo change-status el PATCH lleva solo el estado y el motivo', async () => {
    const { dialog, form } = await mountModal([VIEW, STATUS])
    expect(control(dialog, 'Nombre').disabled).toBe(true)
    await setChecked(dialog, 'Activo', false)
    await setValue(control(dialog, 'Motivo de la desactivación'), 'Obsoleto')
    await submit(form)
    expect(patches()[0]![2]).toEqual({ is_active: false, activity_reason: 'Obsoleto' })
  })

  it('el formulario completo de la sesión de prueba permite guardar', async () => {
    expect((await mountModal(ALL_CONSENT_DOCUMENTS_TAGS)).dialog.textContent).toContain('Guardar cambios')
  })
})

describe('versionado desde el modal del documento', () => {
  it('"Nueva versión" exige create-version', async () => {
    expect(labels((await mountModal([VIEW])).dialog)).not.toContain('Nueva versión')
    document.body.innerHTML = ''
    expect(labels((await mountModal([VIEW, CREATE_VERSION])).dialog)).toContain('Nueva versión')
  })

  it('"Publicar" exige publish-version y "Retirar" retire-version', async () => {
    const versions = [version(), version({ id: 'v0', version_number: 0, status: 'published', published_at: '2026-10-01T00:00:00Z' })]
    const none = labels((await mountModal([VIEW], versions)).dialog)
    expect(none).not.toContain('Publicar')
    expect(none).not.toContain('Retirar')
    document.body.innerHTML = ''
    const publish = labels((await mountModal([VIEW, PUBLISH], versions)).dialog)
    expect(publish).toContain('Publicar')
    expect(publish).not.toContain('Retirar')
    document.body.innerHTML = ''
    const retire = labels((await mountModal([VIEW, RETIRE], versions)).dialog)
    expect(retire).toContain('Retirar')
    expect(retire).not.toContain('Publicar')
  })

  it('el borrador ofrece "Editar" con edit-version y "Ver" sin él', async () => {
    expect(labels((await mountModal([VIEW], [version()])).dialog)).not.toContain('Editar')
    document.body.innerHTML = ''
    expect(labels((await mountModal([VIEW, EDIT_VERSION], [version()])).dialog)).toContain('Editar')
  })
})

describe('editor de versión', () => {
  async function mountEditor(tags: string[], v = version()) {
    fake.routes['GET /consent-documents/d1/versions'] = fakePage([v])
    signInWith(tags)
    const wrapper = await mountSuspended(VersionEditorPage, { route: '/consent-documents/d1/versions/v1', attachTo: document.body })
    await flushAll()
    return wrapper.element.parentElement as HTMLElement
  }

  it('sin edit-version queda en solo lectura: campos bloqueados, sin "Guardar borrador" ni controles del PDF', async () => {
    const root = await mountEditor([VIEW])
    expect(labels(root)).not.toContain('Guardar borrador')
    expect(root.querySelector('fieldset')!.disabled).toBe(true)
    for (const text of ['Reemplazar', 'Quitar', 'Adjuntar PDF']) expect(labels(root)).not.toContain(text)
    expect(labels(root)).toContain('Descargar')
  })

  it('con edit-version el borrador se edita, guarda y gestiona su PDF', async () => {
    const root = await mountEditor([VIEW, EDIT_VERSION])
    expect(labels(root)).toContain('Guardar borrador')
    expect(root.querySelector('fieldset')!.disabled).toBe(false)
    expect(labels(root)).toContain('Reemplazar')
    expect(labels(root)).toContain('Quitar')
  })

  it('Publicar y Retirar del editor exigen su tag', async () => {
    expect(labels(await mountEditor([VIEW, EDIT_VERSION]))).not.toContain('Publicar')
    document.body.innerHTML = ''
    expect(labels(await mountEditor([VIEW, PUBLISH]))).toContain('Publicar')
    document.body.innerHTML = ''
    const published = version({ status: 'published', published_at: '2026-10-01T00:00:00Z' })
    expect(labels(await mountEditor([VIEW], published))).not.toContain('Retirar')
    document.body.innerHTML = ''
    expect(labels(await mountEditor([VIEW, RETIRE], published))).toContain('Retirar')
  })
})
