import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import DefaultLayout from '~/layouts/default.vue'
import { button, control, flushAll, setChecked, setValue } from '#andromeda/testing/dom'
import { fakePage } from '~/testing/fakeApi'
import { ALL_PRINT_LABELS_TAGS } from '~/testing/session'
import { signInWith } from '#leo-client/testing/session'
import type { PrintLabelRead, PrintLabelVersionRead } from '../types/print-labels'
import PrintLabelFormModal from './PrintLabelFormModal.vue'
import PrintLabelsPage from '../pages/print-labels/index.vue'
import VersionEditorPage from '../pages/print-labels/[id]/versions/[versionId].vue'

const fake = await vi.hoisted(async () => (await import('~/testing/fakeApi')).createFakeApi())
mockNuxtImport('useLeoAppApi', () => () => fake.api)

enableAutoUnmount(afterEach)

const LABEL: PrintLabelRead = {
  id: 'l1', code: 'TUBO', name: 'Etiqueta de tubo', description: null, is_active: true,
  created_at: '2026-10-01T00:00:00Z', updated_at: '2026-10-01T00:00:00Z'
}

function version(overrides: Partial<PrintLabelVersionRead> = {}): PrintLabelVersionRead {
  return {
    id: 'v1', print_label_id: 'l1', version_number: 1, status: 'draft', published_at: null, change_notes: null,
    width_mm: 50, height_mm: 25, dpi: 203, output_format: 'zpl', barcode_type: null, copies: 1,
    template_content: '^XA^FD{{patient_name}}^FS^XZ', placeholders: {},
    created_at: '2026-10-01T00:00:00Z', updated_at: '2026-10-01T00:00:00Z',
    ...overrides
  }
}

const VIEW = 'vladimir.print-labels.view'
const EDIT = 'vladimir.print-labels.edit'
const STATUS = 'vladimir.print-labels.change-status'
const CREATE_VERSION = 'vladimir.print-labels.create-version'
const EDIT_VERSION = 'vladimir.print-labels.edit-version'
const PUBLISH = 'vladimir.print-labels.publish-version'
const RETIRE = 'vladimir.print-labels.retire-version'

beforeEach(() => {
  fake.reset()
  invalidateCaches()
  clearNuxtData()
  document.body.innerHTML = ''
  fake.routes['GET /print-labels'] = fakePage([LABEL])
  fake.routes['GET /print-labels/l1'] = LABEL
})

const patches = () => fake.requests.mock.calls.filter(([method]) => method === 'PATCH')
async function submit(form: HTMLFormElement) {
  form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
  await flushAll()
}

async function mountPage(tags: string[]) {
  signInWith(tags)
  const wrapper = await mountSuspended(PrintLabelsPage)
  await flushAll()
  return wrapper
}

async function mountModal(tags: string[], versions: PrintLabelVersionRead[] = []) {
  fake.routes['GET /print-labels/l1/versions'] = fakePage(versions)
  signInWith(tags)
  await mountSuspended(PrintLabelFormModal, { props: { open: true, entity: LABEL }, attachTo: document.body })
  await flushAll()
  const dialog = document.body.querySelector<HTMLElement>('[role="dialog"]')!
  return { dialog, form: dialog.querySelector('form')! }
}

const labels = (root: ParentNode) => [...root.querySelectorAll('a, button')].map(el => el.textContent?.trim())

describe('ruta y menú de print-labels', () => {
  it('las páginas (listado y editor) exigen el tag view', () => {
    const meta = (path: string) => (useRouter().resolve(path).meta as { leo?: { tag?: string } }).leo?.tag
    expect(meta('/print-labels')).toBe(VIEW)
    expect(meta('/print-labels/l1/versions/v1')).toBe(VIEW)
  })

  it('el ítem "Etiquetas de impresión" aparece con view y no sin él', async () => {
    signInWith([VIEW])
    const withView = await mountSuspended(DefaultLayout)
    expect(withView.findAll('a').find(a => a.text() === 'Etiquetas de impresión')?.attributes('href')).toBe('/print-labels')

    signInWith([PUBLISH])
    expect((await mountSuspended(DefaultLayout)).findAll('a').map(a => a.text())).not.toContain('Etiquetas de impresión')
  })
})

describe('listado y datos de la etiqueta', () => {
  it('"Nueva etiqueta" exige create', async () => {
    expect((await mountPage([VIEW])).text()).not.toContain('Nueva etiqueta')
    expect((await mountPage([VIEW, 'vladimir.print-labels.create'])).text()).toContain('Nueva etiqueta')
  })

  it('solo con view la acción es "Ver"; con edit o permisos de versión, "Ver / Editar"', async () => {
    expect((await mountPage([VIEW])).findAll('button').map(b => b.text())).toContain('Ver')
    expect((await mountPage([VIEW, EDIT])).findAll('button').map(b => b.text())).toContain('Ver / Editar')
    expect((await mountPage([VIEW, PUBLISH])).findAll('button').map(b => b.text())).toContain('Ver / Editar')
  })

  it('con solo view el modal es de lectura (campos bloqueados, "Cerrar", sin "Activa")', async () => {
    const { dialog } = await mountModal([VIEW])
    expect(dialog.textContent).not.toContain('Guardar cambios')
    expect(dialog.textContent).not.toContain('Activa')
    expect(() => button(dialog, 'Cerrar')).not.toThrow()
    expect(control(dialog, 'Nombre').disabled).toBe(true)
  })

  it('con edit el PATCH lleva los datos y no is_active', async () => {
    const { dialog, form } = await mountModal([VIEW, EDIT])
    await setValue(control(dialog, 'Nombre'), 'Etiqueta nueva')
    await submit(form)
    const [, path, body] = patches()[0]!
    expect(path).toBe('/print-labels/l1')
    expect(body).toMatchObject({ name: 'Etiqueta nueva', code: 'TUBO' })
    expect(body).not.toHaveProperty('is_active')
  })

  it('con solo change-status el PATCH lleva solo el estado y el motivo', async () => {
    const { dialog, form } = await mountModal([VIEW, STATUS])
    expect(control(dialog, 'Nombre').disabled).toBe(true)
    await setChecked(dialog, 'Activa', false)
    await setValue(control(dialog, 'Motivo de la desactivación'), 'Obsoleta')
    await submit(form)
    expect(patches()[0]![2]).toEqual({ is_active: false, activity_reason: 'Obsoleta' })
  })

  it('el formulario completo de la sesión de prueba permite guardar', async () => {
    expect((await mountModal(ALL_PRINT_LABELS_TAGS)).dialog.textContent).toContain('Guardar cambios')
  })
})

describe('versionado desde el modal de la etiqueta', () => {
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
    fake.routes['GET /print-labels/l1/versions'] = fakePage([v])
    signInWith(tags)
    const wrapper = await mountSuspended(VersionEditorPage, { route: '/print-labels/l1/versions/v1', attachTo: document.body })
    await flushAll()
    return wrapper.element.parentElement as HTMLElement
  }

  it('sin edit-version queda en solo lectura: campos bloqueados y sin "Guardar borrador"', async () => {
    const root = await mountEditor([VIEW])
    expect(labels(root)).not.toContain('Guardar borrador')
    expect(root.querySelector('fieldset')!.disabled).toBe(true)
  })

  it('con edit-version el borrador se edita y guarda', async () => {
    const root = await mountEditor([VIEW, EDIT_VERSION])
    expect(labels(root)).toContain('Guardar borrador')
    expect(root.querySelector('fieldset')!.disabled).toBe(false)
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
