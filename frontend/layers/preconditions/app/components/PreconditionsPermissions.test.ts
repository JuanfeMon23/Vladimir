import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import DefaultLayout from '~/layouts/default.vue'
import { button, control, flushAll, setChecked, setValue } from '~/testing/dom'
import { fakePage } from '~/testing/fakeApi'
import { ALL_PRECONDITIONS_TAGS, signInWith } from '~/testing/session'
import type { PreconditionRead } from '../types/preconditions'
import PreconditionFormModal from './PreconditionFormModal.vue'
import PreconditionsPage from '../pages/preconditions/index.vue'

const fake = await vi.hoisted(async () => (await import('~/testing/fakeApi')).createFakeApi())
mockNuxtImport('useApi', () => () => fake.api)

enableAutoUnmount(afterEach)

const ITEM: PreconditionRead = {
  id: 'i1', parent_id: 'r1', kind: 'condition', code: 'AGUA', name: 'Solo agua', category: 'ayuno',
  is_active: true, created_at: '2026-10-01T00:00:00Z', updated_at: '2026-10-01T00:00:00Z', items: null
}
const ROOT: PreconditionRead = {
  id: 'r1', parent_id: null, kind: 'precondition', code: 'AYU', name: 'Ayuno', category: 'ayuno',
  is_active: true, created_at: '2026-10-01T00:00:00Z', updated_at: '2026-10-01T00:00:00Z', items: [ITEM]
}

const VIEW = 'vladimir.preconditions.view'
const EDIT = 'vladimir.preconditions.edit'
const STATUS = 'vladimir.preconditions.change-status'
const ADD_ITEM = 'vladimir.preconditions.add-item'

beforeEach(() => {
  fake.reset()
  invalidateCaches()
  clearNuxtData()
  document.body.innerHTML = ''
  fake.routes['GET /preconditions'] = fakePage([ROOT])
  fake.routes['GET /preconditions/r1'] = ROOT
})

async function mountPage(tags: string[]) {
  signInWith(tags)
  const wrapper = await mountSuspended(PreconditionsPage)
  await flushAll()
  // Despliega la raíz para ver sus acciones.
  await wrapper.find('button[aria-expanded]').trigger('click')
  await flushAll()
  return wrapper
}

async function mountModal(tags: string[], entity: PreconditionRead | null = ROOT, parent: PreconditionRead | null = null) {
  signInWith(tags)
  await mountSuspended(PreconditionFormModal, { props: { open: true, entity, parent }, attachTo: document.body })
  await flushAll()
  const dialog = document.body.querySelector<HTMLElement>('[role="dialog"]')!
  return { dialog, form: dialog.querySelector('form')! }
}

const patches = () => fake.requests.mock.calls.filter(([method]) => method === 'PATCH')

describe('ruta y menú de preconditions', () => {
  it('la página exige el tag view', () => {
    expect((useRouter().resolve('/preconditions').meta as { leo?: { tag?: string } }).leo?.tag).toBe(VIEW)
  })

  it('el ítem "Precondiciones" aparece con view y no sin él (los módulos con view siguen)', async () => {
    signInWith([VIEW])
    const withView = await mountSuspended(DefaultLayout)
    expect(withView.findAll('a').find(a => a.text() === 'Precondiciones')?.attributes('href')).toBe('/preconditions')

    signInWith(['vladimir.preconditions.create', 'vladimir.lab-tests.view'])
    const labels = (await mountSuspended(DefaultLayout)).findAll('a').map(a => a.text())
    expect(labels).not.toContain('Precondiciones')
    expect(labels).toContain('Exámenes')
  })
})

describe('listado de precondiciones', () => {
  it('sin create no hay botón "Nueva precondición"; con create sí', async () => {
    expect((await mountPage([VIEW])).text()).not.toContain('Nueva precondición')
    expect((await mountPage([VIEW, 'vladimir.preconditions.create'])).text()).toContain('Nueva precondición')
  })

  it('solo con view las acciones son "Ver"; con edit, "Ver / Editar" y "Editar"', async () => {
    const buttons = async (tags: string[]) => (await mountPage(tags)).findAll('button').map(b => b.text())
    const readOnly = await buttons([VIEW])
    expect(readOnly.filter(t => t === 'Ver')).toHaveLength(2)
    expect(readOnly.some(t => t.includes('Editar'))).toBe(false)
    const edit = await buttons([VIEW, EDIT])
    expect(edit).toContain('Ver / Editar')
    expect(edit).toContain('Editar')
  })

  it('con solo add-item la fila ofrece "Ver / Editar" (para llegar a "Agregar ítem")', async () => {
    expect((await mountPage([VIEW, ADD_ITEM])).text()).toContain('Ver / Editar')
  })
})

describe('detalle/edición de una precondición', () => {
  it('con solo view el modal es de lectura: campos bloqueados, "Cerrar", sin "Activa" ni "Agregar ítem"', async () => {
    const { dialog } = await mountModal([VIEW])
    expect(dialog.textContent).not.toContain('Guardar cambios')
    expect(dialog.textContent).not.toContain('Agregar ítem')
    expect(dialog.textContent).not.toContain('Activa')
    expect(() => button(dialog, 'Cerrar')).not.toThrow()
    expect(control(dialog, 'Nombre').disabled).toBe(true)
  })

  it('"Agregar ítem" exige add-item', async () => {
    expect((await mountModal([VIEW, EDIT])).dialog.textContent).not.toContain('Agregar ítem')
    document.body.innerHTML = ''
    expect((await mountModal([VIEW, ADD_ITEM])).dialog.textContent).toContain('Agregar ítem')
  })

  it('con edit el PATCH lleva los datos y no is_active', async () => {
    const { dialog, form } = await mountModal([VIEW, EDIT])
    expect(dialog.textContent).not.toContain('Activa')
    await setValue(control(dialog, 'Nombre'), 'Ayuno 8 h')
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
    await flushAll()
    const [, path, body] = patches()[0]!
    expect(path).toBe('/preconditions/r1')
    expect(body).toMatchObject({ name: 'Ayuno 8 h', code: 'AYU' })
    expect(body).not.toHaveProperty('is_active')
  })

  it('con solo change-status el PATCH lleva solo el estado y el motivo', async () => {
    const { dialog, form } = await mountModal([VIEW, STATUS])
    expect(control(dialog, 'Nombre').disabled).toBe(true)
    await setChecked(dialog, 'Activa', false)
    await setValue(control(dialog, 'Motivo de la desactivación'), 'Obsoleta')
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
    await flushAll()
    expect(patches()[0]![2]).toEqual({ is_active: false, activity_reason: 'Obsoleta' })
  })

  it('un ítem nuevo bajo una raíz se crea con add-item (POST a /items)', async () => {
    const { dialog, form } = await mountModal([VIEW, ADD_ITEM], null, ROOT)
    await setValue(control(dialog, 'Código'), 'JUGO')
    await setValue(control(dialog, 'Nombre'), 'Sin jugo')
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
    await flushAll()
    expect(fake.bodies('POST', '/preconditions/r1/items')).toHaveLength(1)
  })

  it('el formulario completo de la sesión de prueba permite guardar', async () => {
    const { dialog } = await mountModal(ALL_PRECONDITIONS_TAGS)
    expect(dialog.textContent).toContain('Guardar cambios')
  })
})
