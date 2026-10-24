import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Component } from 'vue'
import DefaultLayout from '~/layouts/default.vue'
import { button, control, flushAll, setChecked, setValue } from '#andromeda/testing/dom'
import { fakePage } from '~/testing/fakeApi'
import { ALL_LAB_TESTS_TAGS, LAB_TEST_SELECTOR_VIEW_TAGS } from '~/testing/session'
import { signInWith } from '#leo-client/testing/session'
import type { LabTestRead } from '../types/lab-tests'
import LabTestConsentDocumentsEditor from './LabTestConsentDocumentsEditor.vue'
import LabTestFormModal from './LabTestFormModal.vue'
import LabTestPreconditionsEditor from './LabTestPreconditionsEditor.vue'
import LabTestSampleTypesEditor from './LabTestSampleTypesEditor.vue'
import LabTestsPage from '../pages/lab-tests/index.vue'

const fake = await vi.hoisted(async () => (await import('~/testing/fakeApi')).createFakeApi())
mockNuxtImport('useLeoAppApi', () => () => fake.api)

enableAutoUnmount(afterEach)

const TEST: LabTestRead = {
  id: 't1', code: 'GLU', name: 'Glucosa', abbreviation: null, description: null, area_id: 'a1', method: null,
  turnaround_hours: 24, loinc_code: null, cups_code: null, print_label_version_id: null, result_template_version_id: null,
  is_active: true, created_at: '2026-10-01T00:00:00Z', updated_at: '2026-10-01T00:00:00Z',
  preconditions: [], sample_types: [], consent_documents: []
}

const L = (verb: string) => `vladimir.lab-tests.${verb}`
const VIEW = L('view')
const SELECTORS = LAB_TEST_SELECTOR_VIEW_TAGS

beforeEach(() => {
  fake.reset()
  invalidateCaches()
  clearNuxtData()
  document.body.innerHTML = ''
  fake.routes['GET /lab-tests'] = fakePage([TEST])
  fake.routes['GET /lab-areas'] = fakePage([{ id: 'a1', code: 'HEM', name: 'Hematología', is_active: true }])
  fake.routes['GET /print-labels'] = fakePage([])
  fake.routes['GET /result-templates'] = fakePage([])
  fake.routes['GET /preconditions'] = fakePage([{ id: 'p1', code: 'AYU', name: 'Ayuno', is_active: true, items: [] }])
  fake.routes['GET /samples'] = fakePage([
    { id: 's1', code: 'SAN', name: 'Sangre', is_active: true, types: [{ id: 'suero', code: 'SUE', name: 'Suero', specimen: 'serum', is_active: true }] }
  ])
  fake.routes['GET /consent-documents'] = fakePage([])
  fake.routes['GET /lab-tests/t1/preconditions'] = []
  fake.routes['GET /lab-tests/t1/sample-types'] = []
  fake.routes['GET /lab-tests/t1/consent-documents'] = []
})

const requested = (path: string) => fake.requests.mock.calls.some(([method, p]) => method === 'GET' && p === path)
const patches = () => fake.requests.mock.calls.filter(([method]) => method === 'PATCH')

async function mountPage(tags: string[]) {
  signInWith(tags)
  const wrapper = await mountSuspended(LabTestsPage)
  await flushAll()
  return wrapper
}

async function mountModal(tags: string[], entity: LabTestRead | null = TEST) {
  signInWith(tags)
  await mountSuspended(LabTestFormModal, { props: { open: true, entity }, attachTo: document.body })
  await flushAll()
  const dialog = document.body.querySelector<HTMLElement>('[role="dialog"]')!
  return { dialog, form: dialog.querySelector('form')! }
}

async function mountEditor(editor: Component, tags: string[]) {
  signInWith(tags)
  const wrapper = await mountSuspended(editor, { props: { labTestId: 't1' }, attachTo: document.body })
  await flushAll()
  return wrapper.element.parentElement as HTMLElement
}

describe('ruta y menú de lab-tests', () => {
  it('la página exige el tag view', () => {
    expect((useRouter().resolve('/lab-tests').meta as { leo?: { tag?: string } }).leo?.tag).toBe(VIEW)
  })

  it('el ítem "Exámenes" aparece con view y no sin él (los módulos con view siguen)', async () => {
    signInWith([VIEW])
    const withView = await mountSuspended(DefaultLayout)
    expect(withView.findAll('a').find(a => a.text() === 'Exámenes')?.attributes('href')).toBe('/lab-tests')

    signInWith([L('create'), 'vladimir.staff.view'])
    const labels = (await mountSuspended(DefaultLayout)).findAll('a').map(a => a.text())
    expect(labels).not.toContain('Exámenes')
    expect(labels).toContain('Personal')
  })
})

describe('listado de exámenes', () => {
  it('sin create no hay botón "Nuevo examen"; con create sí', async () => {
    expect((await mountPage([VIEW])).text()).not.toContain('Nuevo examen')
    expect((await mountPage([VIEW, L('create')])).text()).toContain('Nuevo examen')
  })

  it('solo con view la acción de fila es "Ver"; con cualquier permiso de cambio, "Ver / Editar"', async () => {
    const readOnly = (await mountPage([VIEW])).text()
    expect(readOnly).not.toContain('Ver / Editar')
    expect(readOnly).toMatch(/Ver(?! \/)/)
    expect((await mountPage([VIEW, L('set-consent-documents')])).text()).toContain('Ver / Editar')
  })

  it('sin view de áreas no pide el catálogo y no muestra el filtro', async () => {
    const wrapper = await mountPage([VIEW])
    expect(requested('/lab-areas')).toBe(false)
    expect(wrapper.find('#lab-test-area-filter').exists()).toBe(false)
  })

  it('con view de áreas pide el catálogo y el filtro queda activo', async () => {
    const wrapper = await mountPage([VIEW, MODULE_VIEW.labAreas.tag])
    expect(requested('/lab-areas')).toBe(true)
    expect(wrapper.find<HTMLSelectElement>('#lab-test-area-filter').element.disabled).toBe(false)
  })
})

describe('detalle/edición de un examen', () => {
  it('con solo view el modal es de lectura: campos bloqueados, "Cerrar", sin "Activo"', async () => {
    const { dialog } = await mountModal([VIEW, ...SELECTORS])
    expect(dialog.textContent).not.toContain('Guardar cambios')
    expect(dialog.textContent).not.toContain('Activo')
    expect(() => button(dialog, 'Cerrar')).not.toThrow()
    expect(control(dialog, 'Nombre').disabled).toBe(true)
    expect(control(dialog, 'Área').disabled).toBe(true)
  })

  it('con edit el PATCH lleva los datos y no is_active', async () => {
    const { dialog, form } = await mountModal([VIEW, L('edit'), ...SELECTORS])
    expect(dialog.textContent).not.toContain('Activo')
    await setValue(control(dialog, 'Nombre'), 'Glucosa basal')
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
    await flushAll()
    const [, path, body] = patches()[0]!
    expect(path).toBe('/lab-tests/t1')
    expect(body).toMatchObject({ name: 'Glucosa basal', code: 'GLU', area_id: 'a1' })
    expect(body).not.toHaveProperty('is_active')
    expect(body).not.toHaveProperty('sample_types')
  })

  it('con solo change-status los datos están bloqueados y el PATCH solo lleva el estado y el motivo', async () => {
    const { dialog, form } = await mountModal([VIEW, L('change-status'), ...SELECTORS])
    expect(control(dialog, 'Nombre').disabled).toBe(true)
    await setChecked(dialog, 'Activo', false)
    await setValue(control(dialog, 'Motivo de la desactivación'), 'Reemplazado')
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
    await flushAll()
    expect(patches()[0]![2]).toEqual({ is_active: false, activity_reason: 'Reemplazado' })
  })

  it('crear con el formulario completo no bloquea nada', async () => {
    const { dialog } = await mountModal([...ALL_LAB_TESTS_TAGS, ...SELECTORS], null)
    expect(control(dialog, 'Nombre').disabled).toBe(false)
    expect(control(dialog, 'Área').disabled).toBe(false)
    expect(dialog.textContent).toContain('Activo')
  })
})

describe('selectores de otros módulos sin su view', () => {
  it('área, etiqueta, plantilla y muestras: avisan, no piden el catálogo y no muestran el selector de área (los demás se deshabilitan)', async () => {
    const { dialog } = await mountModal([...ALL_LAB_TESTS_TAGS], null)
    for (const label of ['áreas', 'etiquetas de impresión', 'plantillas de resultados', 'muestras']) {
      expect(dialog.textContent).toContain(`No tienes permiso para consultar ${label}.`)
    }
    for (const path of ['/lab-areas', '/print-labels', '/result-templates', '/samples']) expect(requested(path)).toBe(false)
    expect(() => control(dialog, 'Área')).toThrow()
    expect(control(dialog, 'Etiqueta').disabled).toBe(true)
    expect(control(dialog, 'Plantilla').disabled).toBe(true)
  })

  it('al editar, la etiqueta ya asignada viaja intacta aunque no se pueda consultar', async () => {
    const assigned = { ...TEST, print_label_version_id: 'plv1' }
    const { form } = await mountModal([VIEW, L('edit')], assigned)
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
    await flushAll()
    expect(requested('/print-label-versions/plv1')).toBe(false)
    expect(patches()[0]![2]).toMatchObject({ print_label_version_id: 'plv1' })
  })

  it('con los view de los selectores los pide y no avisa', async () => {
    const { dialog } = await mountModal([...ALL_LAB_TESTS_TAGS, ...SELECTORS], null)
    expect(dialog.textContent).not.toContain('No tienes permiso para consultar')
    for (const path of ['/lab-areas', '/print-labels', '/result-templates', '/samples']) expect(requested(path)).toBe(true)
  })
})

const TABS = [
  { name: 'precondiciones', editor: LabTestPreconditionsEditor, save: 'set-preconditions', view: 'vladimir.preconditions.view', catalog: '/preconditions', submit: 'Guardar precondiciones', module: 'precondiciones' },
  { name: 'tipos de muestra', editor: LabTestSampleTypesEditor, save: 'set-sample-types', view: 'vladimir.samples.view', catalog: '/samples', submit: 'Guardar tipos de muestra', module: 'muestras' },
  { name: 'documentos', editor: LabTestConsentDocumentsEditor, save: 'set-consent-documents', view: 'vladimir.consent-documents.view', catalog: '/consent-documents', submit: 'Guardar documentos', module: 'documentos a firmar' }
]

describe.each(TABS)('pestaña de asignaciones: $name', ({ editor, save, view, catalog, submit, module }) => {
  it('con el tag de asignar y el view del catálogo se puede guardar', async () => {
    const root = await mountEditor(editor, [VIEW, L(save), view])
    expect(() => button(root, submit)).not.toThrow()
    expect(root.textContent).not.toContain('No tienes permiso')
  })

  it('sin el tag de asignar es de solo lectura: sin botón y aviso con el nombre del permiso', async () => {
    const root = await mountEditor(editor, [VIEW, view])
    expect(() => button(root, submit)).toThrow()
    expect(root.textContent).toContain('Solo puedes consultar')
    expect(root.textContent).toContain('No tienes permiso para: Asignar')
  })

  it('sin el view del módulo del catálogo avisa, no lo pide y no ofrece guardar', async () => {
    const root = await mountEditor(editor, [VIEW, L(save)])
    expect(root.textContent).toContain(`No tienes permiso para consultar ${module}.`)
    expect(requested(catalog)).toBe(false)
    expect(() => button(root, submit)).toThrow()
  })
})

describe('controles de las pestañas sin el tag de asignar', () => {
  it('las filas quedan deshabilitadas (checkbox dentro del fieldset bloqueado)', async () => {
    fake.routes['GET /lab-tests/t1/sample-types'] = []
    const root = await mountEditor(LabTestSampleTypesEditor, [VIEW, 'vladimir.samples.view'])
    const boxes = [...root.querySelectorAll<HTMLInputElement>('li input[type="checkbox"]')]
    expect(boxes.length).toBeGreaterThan(0)
    expect(boxes.every(box => box.closest('fieldset')?.disabled === true)).toBe(true)
  })
})
