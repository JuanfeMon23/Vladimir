import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import DefaultLayout from '~/layouts/default.vue'
import { button, control, flushAll, setChecked, setValue } from '#andromeda/testing/dom'
import { fakePage } from '~/testing/fakeApi'
import { ALL_RESULT_TEMPLATES_TAGS } from '~/testing/session'
import { signInWith } from '#leo-client/testing/session'
import type {
  AnalyteRead, ResultOptionRead, ResultOptionSetRead, ResultTemplateRead,
  ResultTemplateSectionRead, ResultTemplateVersionRead, UnitRead
} from '../types/result-templates'
import AnalyteFormModal from './AnalyteFormModal.vue'
import ResultOptionSetFormModal from './ResultOptionSetFormModal.vue'
import ResultTemplateFormModal from './ResultTemplateFormModal.vue'
import UnitFormModal from './UnitFormModal.vue'
import AnalytesPage from '../pages/analytes/index.vue'
import ResultOptionSetsPage from '../pages/result-option-sets/index.vue'
import ResultTemplatesPage from '../pages/result-templates/index.vue'
import UnitsPage from '../pages/units/index.vue'
import VersionEditorPage from '../pages/result-templates/[id]/versions/[versionId].vue'

const fake = await vi.hoisted(async () => (await import('~/testing/fakeApi')).createFakeApi())
mockNuxtImport('useLeoAppApi', () => () => fake.api)

enableAutoUnmount(afterEach)

const STAMPS = { created_at: '2026-10-01T00:00:00Z', updated_at: '2026-10-01T00:00:00Z' }
const TEMPLATE: ResultTemplateRead = { id: 't1', code: 'HEMO', name: 'Hemograma', description: null, is_active: true, ...STAMPS }
const UNIT: UnitRead = { id: 'u1', code: 'mg/dL', symbol: 'mg/dL', name: 'Miligramos por decilitro', is_active: true, ...STAMPS }
const ANALYTE: AnalyteRead = {
  id: 'a1', code: 'GLU', name: 'Glucosa', loinc_code: null, default_unit_id: null, description: null, is_active: true, ...STAMPS
}
const OPTION_SET: ResultOptionSetRead = { id: 'o1', code: 'POSNEG', name: 'Positivo/Negativo', is_active: true, ...STAMPS }
const OPTION: ResultOptionRead = {
  id: 'op1', option_set_id: 'o1', code: 'POS', label: 'Positivo', sort_order: 0, is_abnormal: true, is_active: true, ...STAMPS
}
const SECTION: ResultTemplateSectionRead = { id: 's1', version_id: 'v1', name: 'Serie roja', sort_order: 0, is_active: true, ...STAMPS }

function version(overrides: Partial<ResultTemplateVersionRead> = {}): ResultTemplateVersionRead {
  return {
    id: 'v1', result_template_id: 't1', version_number: 1, status: 'draft', published_at: null, change_notes: null,
    report_settings: {}, ...STAMPS, ...overrides
  }
}

const P = 'vladimir.result-templates.'
const VIEW = `${P}view`
const EDIT = `${P}edit`
const STATUS = `${P}change-status`
const CREATE_VERSION = `${P}create-version`
const EDIT_VERSION = `${P}edit-version`
const PUBLISH = `${P}publish-version`
const RETIRE = `${P}retire-version`
const EDIT_CONTENT = `${P}edit-content`
const MANAGE_UNITS = `${P}manage-units`
const MANAGE_ANALYTES = `${P}manage-analytes`
const MANAGE_SETS = `${P}manage-option-sets`

beforeEach(() => {
  fake.reset()
  invalidateCaches()
  clearNuxtData()
  document.body.innerHTML = ''
  fake.routes['GET /result-templates'] = fakePage([TEMPLATE])
  fake.routes['GET /result-templates/t1'] = TEMPLATE
  fake.routes['GET /units'] = fakePage([UNIT])
  fake.routes['GET /analytes'] = fakePage([ANALYTE])
  fake.routes['GET /result-option-sets'] = fakePage([OPTION_SET])
  fake.routes['GET /result-option-sets/o1/options'] = fakePage([OPTION])
})

const patches = () => fake.requests.mock.calls.filter(([method]) => method === 'PATCH')
async function submit(form: HTMLFormElement) {
  form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
  await flushAll()
}
const labels = (root: ParentNode) => [...root.querySelectorAll('a, button')].map(el => el.textContent?.trim())

async function mountPage(component: object, tags: string[]) {
  signInWith(tags)
  const wrapper = await mountSuspended(component)
  await flushAll()
  return wrapper
}

async function mountModal(component: object, props: object, tags: string[]) {
  signInWith(tags)
  await mountSuspended(component, { props: { open: true, ...props }, attachTo: document.body })
  await flushAll()
  const dialog = document.body.querySelector<HTMLElement>('[role="dialog"]')!
  return { dialog, form: dialog.querySelector('form')! }
}

describe('rutas y menú de result-templates', () => {
  it('todas las pantallas del módulo exigen el tag view', () => {
    const meta = (path: string) => (useRouter().resolve(path).meta as { leo?: { tag?: string } }).leo?.tag
    for (const path of ['/result-templates', '/analytes', '/units', '/result-option-sets', '/result-templates/t1/versions/v1']) {
      expect(meta(path), path).toBe(VIEW)
    }
  })

  it('los 4 ítems del módulo aparecen con view y no sin él', async () => {
    const names = ['Analitos', 'Unidades de medida', 'Conjuntos de opciones', 'Plantillas de resultados']
    signInWith([VIEW])
    const withView = (await mountSuspended(DefaultLayout)).findAll('a').map(a => a.text())
    for (const name of names) expect(withView).toContain(name)

    signInWith([MANAGE_UNITS, EDIT_CONTENT, 'vladimir.lab-tests.view'])
    const without = (await mountSuspended(DefaultLayout)).findAll('a').map(a => a.text())
    for (const name of names) expect(without).not.toContain(name)
    expect(without).toContain('Exámenes')
  })
})

describe('plantillas: listado y datos', () => {
  it('"Nueva plantilla" exige create', async () => {
    expect((await mountPage(ResultTemplatesPage, [VIEW])).text()).not.toContain('Nueva plantilla')
    expect((await mountPage(ResultTemplatesPage, [VIEW, `${P}create`])).text()).toContain('Nueva plantilla')
  })

  it('solo con view la acción es "Ver"; con edit-content, "Ver / Editar"', async () => {
    expect((await mountPage(ResultTemplatesPage, [VIEW])).findAll('button').map(b => b.text())).toContain('Ver')
    expect((await mountPage(ResultTemplatesPage, [VIEW, EDIT_CONTENT])).findAll('button').map(b => b.text())).toContain('Ver / Editar')
  })

  it('con solo view el modal es de lectura', async () => {
    fake.routes['GET /result-templates/t1/versions'] = fakePage([])
    const { dialog } = await mountModal(ResultTemplateFormModal, { entity: TEMPLATE }, [VIEW])
    expect(dialog.textContent).not.toContain('Guardar cambios')
    expect(dialog.textContent).not.toContain('Activa')
    expect(() => button(dialog, 'Cerrar')).not.toThrow()
    expect(control(dialog, 'Nombre').disabled).toBe(true)
  })

  it('con edit el PATCH lleva los datos y no is_active', async () => {
    fake.routes['GET /result-templates/t1/versions'] = fakePage([])
    const { dialog, form } = await mountModal(ResultTemplateFormModal, { entity: TEMPLATE }, [VIEW, EDIT])
    await setValue(control(dialog, 'Nombre'), 'Hemograma completo')
    await submit(form)
    const [, path, body] = patches()[0]!
    expect(path).toBe('/result-templates/t1')
    expect(body).toMatchObject({ name: 'Hemograma completo', code: 'HEMO' })
    expect(body).not.toHaveProperty('is_active')
  })

  it('con solo change-status el PATCH lleva solo el estado y el motivo', async () => {
    fake.routes['GET /result-templates/t1/versions'] = fakePage([])
    const { dialog, form } = await mountModal(ResultTemplateFormModal, { entity: TEMPLATE }, [VIEW, STATUS])
    expect(control(dialog, 'Nombre').disabled).toBe(true)
    await setChecked(dialog, 'Activa', false)
    await setValue(control(dialog, 'Motivo de la desactivación'), 'Obsoleta')
    await submit(form)
    expect(patches()[0]![2]).toEqual({ is_active: false, activity_reason: 'Obsoleta' })
  })

  it('el formulario completo de la sesión de prueba permite guardar', async () => {
    fake.routes['GET /result-templates/t1/versions'] = fakePage([])
    const { dialog } = await mountModal(ResultTemplateFormModal, { entity: TEMPLATE }, ALL_RESULT_TEMPLATES_TAGS)
    expect(dialog.textContent).toContain('Guardar cambios')
  })
})

describe('plantillas: versionado desde el modal', () => {
  async function mountVersions(tags: string[], versions: ResultTemplateVersionRead[]) {
    fake.routes['GET /result-templates/t1/versions'] = fakePage(versions)
    document.body.innerHTML = ''
    return (await mountModal(ResultTemplateFormModal, { entity: TEMPLATE }, tags)).dialog
  }
  const published = version({ id: 'v0', version_number: 0, status: 'published', published_at: '2026-10-01T00:00:00Z' })

  it('"Nueva versión" exige create-version', async () => {
    expect(labels(await mountVersions([VIEW], []))).not.toContain('Nueva versión')
    expect(labels(await mountVersions([VIEW, CREATE_VERSION], []))).toContain('Nueva versión')
  })

  it('"Publicar" exige publish-version y "Retirar" retire-version', async () => {
    const versions = [version(), published]
    const none = labels(await mountVersions([VIEW], versions))
    expect(none).not.toContain('Publicar')
    expect(none).not.toContain('Retirar')
    const publish = labels(await mountVersions([VIEW, PUBLISH], versions))
    expect(publish).toContain('Publicar')
    expect(publish).not.toContain('Retirar')
    const retire = labels(await mountVersions([VIEW, RETIRE], versions))
    expect(retire).toContain('Retirar')
    expect(retire).not.toContain('Publicar')
  })

  it('el borrador ofrece "Editar" con edit-version y "Ver" sin él', async () => {
    expect(labels(await mountVersions([VIEW], [version()]))).not.toContain('Editar')
    expect(labels(await mountVersions([VIEW, EDIT_VERSION], [version()]))).toContain('Editar')
  })
})

describe('editor de versión de plantilla', () => {
  async function mountEditor(tags: string[], v = version()) {
    fake.routes['GET /result-templates/t1/versions'] = fakePage([v])
    fake.routes['GET /result-templates/t1/versions/v1/sections'] = [SECTION]
    fake.routes['GET /result-templates/t1/versions/v1/analytes'] = []
    document.body.innerHTML = ''
    signInWith(tags)
    const wrapper = await mountSuspended(VersionEditorPage, { route: '/result-templates/t1/versions/v1', attachTo: document.body })
    await flushAll()
    return wrapper.element.parentElement as HTMLElement
  }

  it('solo con view todo es de lectura: sin guardar datos, sin agregar secciones ni analitos', async () => {
    const root = await mountEditor([VIEW])
    const all = labels(root)
    for (const text of ['Guardar datos generales', 'Agregar sección', 'Agregar analito', 'Publicar']) expect(all).not.toContain(text)
    expect(root.querySelector('fieldset')!.disabled).toBe(true)
  })

  it('edit-version habilita los datos generales pero no el contenido', async () => {
    const root = await mountEditor([VIEW, EDIT_VERSION])
    const all = labels(root)
    expect(all).toContain('Guardar datos generales')
    expect(root.querySelector('fieldset')!.disabled).toBe(false)
    expect(all).not.toContain('Agregar sección')
    expect(all).not.toContain('Agregar analito')
    expect(all).not.toContain('Desactivar')
  })

  it('edit-content habilita secciones y analitos pero no los datos generales', async () => {
    const root = await mountEditor([VIEW, EDIT_CONTENT])
    const all = labels(root)
    expect(all).toContain('Agregar sección')
    expect(all).toContain('Agregar analito')
    expect(all).toContain('Desactivar')
    expect(all).not.toContain('Guardar datos generales')
    expect(root.querySelector('fieldset')!.disabled).toBe(true)
  })

  it('una versión publicada no se edita ni con todos los permisos', async () => {
    const root = await mountEditor(ALL_RESULT_TEMPLATES_TAGS, version({ status: 'published', published_at: '2026-10-01T00:00:00Z' }))
    const all = labels(root)
    for (const text of ['Guardar datos generales', 'Agregar sección', 'Agregar analito']) expect(all).not.toContain(text)
    expect(all).toContain('Retirar')
  })

  it('Publicar y Retirar del editor exigen su tag', async () => {
    expect(labels(await mountEditor([VIEW, EDIT_VERSION]))).not.toContain('Publicar')
    expect(labels(await mountEditor([VIEW, PUBLISH]))).toContain('Publicar')
    const done = version({ status: 'published', published_at: '2026-10-01T00:00:00Z' })
    expect(labels(await mountEditor([VIEW], done))).not.toContain('Retirar')
    expect(labels(await mountEditor([VIEW, RETIRE], done))).toContain('Retirar')
  })
})

describe('catálogos de apoyo: una acción manage-* por catálogo', () => {
  it.each([
    ['unidades', UnitsPage, 'Nueva unidad', MANAGE_UNITS],
    ['analitos', AnalytesPage, 'Nuevo analito', MANAGE_ANALYTES],
    ['conjuntos de opciones', ResultOptionSetsPage, 'Nuevo conjunto', MANAGE_SETS]
  ])('%s: crear y "Ver / Editar" exigen su manage-*, y no el de otro catálogo', async (_name, page, create, manage) => {
    const other = [MANAGE_UNITS, MANAGE_ANALYTES, MANAGE_SETS].filter(tag => tag !== manage)
    const readOnly = await mountPage(page, [VIEW, ...other, EDIT_CONTENT])
    expect(readOnly.text()).not.toContain(create)
    expect(readOnly.findAll('button').map(b => b.text())).toContain('Ver')
    const managed = await mountPage(page, [VIEW, manage])
    expect(managed.text()).toContain(create)
    expect(managed.findAll('button').map(b => b.text())).toContain('Ver / Editar')
  })

  it('unidad: sin manage-units es de lectura; con él el PATCH lleva los datos', async () => {
    const readOnly = await mountModal(UnitFormModal, { entity: UNIT }, [VIEW])
    expect(readOnly.dialog.textContent).not.toContain('Guardar cambios')
    expect(readOnly.dialog.textContent).not.toContain('Activa')
    expect(control(readOnly.dialog, 'Nombre').disabled).toBe(true)
    document.body.innerHTML = ''
    const { dialog, form } = await mountModal(UnitFormModal, { entity: UNIT }, [VIEW, MANAGE_UNITS])
    await setValue(control(dialog, 'Nombre'), 'Miligramo')
    await submit(form)
    expect(patches()[0]![1]).toBe('/units/u1')
    expect(patches()[0]![2]).toMatchObject({ name: 'Miligramo', is_active: true })
  })

  it('analito: sin manage-analytes es de lectura (incluida la unidad por defecto)', async () => {
    const { dialog } = await mountModal(AnalyteFormModal, { entity: ANALYTE }, [VIEW, MANAGE_UNITS])
    expect(dialog.textContent).not.toContain('Guardar cambios')
    expect(control(dialog, 'Nombre').disabled).toBe(true)
    expect(control<HTMLSelectElement>(dialog, 'Unidad por defecto (UCUM)').disabled).toBe(true)
  })

  it('conjunto de opciones: "Agregar opción" y editar opciones exigen manage-option-sets', async () => {
    const readOnly = (await mountModal(ResultOptionSetFormModal, { entity: OPTION_SET }, [VIEW, MANAGE_UNITS])).dialog
    expect(labels(readOnly)).not.toContain('Agregar opción')
    expect(labels(readOnly)).toContain('Ver')
    expect(labels(readOnly)).not.toContain('Editar')
    expect(readOnly.textContent).not.toContain('Guardar cambios')
    document.body.innerHTML = ''
    const managed = (await mountModal(ResultOptionSetFormModal, { entity: OPTION_SET }, [VIEW, MANAGE_SETS])).dialog
    expect(labels(managed)).toContain('Agregar opción')
    expect(labels(managed)).toContain('Editar')
  })
})
