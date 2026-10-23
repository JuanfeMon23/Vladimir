import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import DefaultLayout from '~/layouts/default.vue'
import { button, control, flushAll, setChecked, setValue } from '#andromeda/testing/dom'
import { fakePage } from '~/testing/fakeApi'
import { ALL_STAFF_TAGS } from '~/testing/session'
import { signInWith } from '#leo-client/testing/session'
import type { StaffRead } from '../types/staff'
import StaffFormModal from './StaffFormModal.vue'
import StaffPage from '../pages/staff/index.vue'

const fake = await vi.hoisted(async () => (await import('~/testing/fakeApi')).createFakeApi())
mockNuxtImport('useLeoAppApi', () => () => fake.api)

enableAutoUnmount(afterEach)

const PERSON: StaffRead = {
  id: 'p1', document_type: 'CC', document_number: '1', first_name: 'Ana', last_name: 'Herrera',
  email: null, phone: null, job_title: 'Bacterióloga', professional_license: null, is_active: true,
  created_at: '2026-10-01T00:00:00Z', updated_at: '2026-10-01T00:00:00Z'
}

const VIEW = 'vladimir.staff.view'
const EDIT = 'vladimir.staff.edit'
const STATUS = 'vladimir.staff.change-status'

beforeEach(() => {
  fake.reset()
  invalidateCaches()
  clearNuxtData()
  document.body.innerHTML = ''
  fake.routes['GET /staff'] = fakePage([PERSON])
})

async function mountPage(tags: string[]) {
  signInWith(tags)
  const wrapper = await mountSuspended(StaffPage)
  await flushAll()
  return wrapper
}

async function mountModal(tags: string[], entity: StaffRead | null = PERSON) {
  signInWith(tags)
  await mountSuspended(StaffFormModal, { props: { open: true, entity }, attachTo: document.body })
  await flushAll()
  const dialog = document.body.querySelector<HTMLElement>('[role="dialog"]')!
  return { dialog, form: dialog.querySelector('form')! }
}

const patches = () => fake.requests.mock.calls.filter(([method]) => method === 'PATCH')

describe('ruta y menú de staff', () => {
  it('la página exige el tag view', () => {
    expect((useRouter().resolve('/staff').meta as { leo?: { tag?: string } }).leo?.tag).toBe(VIEW)
  })

  it('el ítem "Personal" aparece con view y no aparece sin él (los módulos con view siguen)', async () => {
    signInWith([VIEW])
    const withView = await mountSuspended(DefaultLayout)
    expect(withView.findAll('a').find(a => a.text() === 'Personal')?.attributes('href')).toBe('/staff')

    signInWith(['vladimir.staff.create', 'vladimir.lab-tests.view'])
    const without = await mountSuspended(DefaultLayout)
    const labels = without.findAll('a').map(a => a.text())
    expect(labels).not.toContain('Personal')
    expect(labels).toContain('Exámenes')
  })
})

describe('listado de personal', () => {
  it('sin create no hay botón "Nuevo"; con create sí', async () => {
    expect((await mountPage([VIEW])).text()).not.toContain('Nuevo')
    expect((await mountPage([VIEW, 'vladimir.staff.create'])).text()).toContain('Nuevo')
  })

  it('solo con view la acción de fila es "Ver"; con edit o change-status, "Ver / Editar"', async () => {
    const readOnly = (await mountPage([VIEW])).text()
    expect(readOnly).not.toContain('Ver / Editar')
    expect(readOnly).toMatch(/Ver(?! \/)/)
    expect((await mountPage([VIEW, EDIT])).text()).toContain('Ver / Editar')
    expect((await mountPage([VIEW, STATUS])).text()).toContain('Ver / Editar')
  })
})

describe('detalle/edición de personal', () => {
  it('con solo view el modal es de lectura: campos deshabilitados, sin "Guardar cambios" y sin "Activo"', async () => {
    const { dialog } = await mountModal([VIEW])
    expect(dialog.textContent).not.toContain('Guardar cambios')
    expect(dialog.textContent).not.toContain('Activo')
    expect(() => button(dialog, 'Cerrar')).not.toThrow()
    expect(control(dialog, 'Nombres').disabled).toBe(true)
  })

  it('con edit los datos son editables, "Activo" no aparece y el PATCH no lleva is_active', async () => {
    const { dialog, form } = await mountModal([VIEW, EDIT])
    expect(control(dialog, 'Nombres').disabled).toBe(false)
    expect(dialog.textContent).not.toContain('Activo')
    await setValue(control(dialog, 'Nombres'), 'Ana María')
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
    await flushAll()
    const [method, path, body] = patches()[0]!
    expect([method, path]).toEqual(['PATCH', '/staff/p1'])
    expect(body).toMatchObject({ first_name: 'Ana María', document_number: '1' })
    expect(body).not.toHaveProperty('is_active')
  })

  it('con solo change-status los datos están bloqueados y el PATCH solo lleva el estado y el motivo', async () => {
    const { dialog, form } = await mountModal([VIEW, STATUS])
    expect(control(dialog, 'Nombres').disabled).toBe(true)
    await setChecked(dialog, 'Activo', false)
    await setValue(control(dialog, 'Motivo de la desactivación'), 'Renuncia')
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
    await flushAll()
    expect(patches()[0]![2]).toEqual({ is_active: false, activity_reason: 'Renuncia' })
  })

  it('crear no exige change-status para el campo "Activo"', async () => {
    const { dialog } = await mountModal([VIEW, 'vladimir.staff.create'], null)
    expect(dialog.textContent).toContain('Activo')
    expect(control(dialog, 'Nombres').disabled).toBe(false)
  })
})

describe('mapa de tags', () => {
  it('la sesión de prueba con todos los tags habilita edición completa', async () => {
    const { dialog } = await mountModal(ALL_STAFF_TAGS)
    expect(dialog.textContent).toContain('Guardar cambios')
    expect(dialog.textContent).toContain('Activo')
  })
})
