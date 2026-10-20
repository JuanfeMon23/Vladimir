import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import DefaultLayout from '~/layouts/default.vue'
import { button, flushAll } from '~/testing/dom'
import { fakePage } from '~/testing/fakeApi'
import { ALL_LAB_AREAS_TAGS, signInWith } from '~/testing/session'
import type { LabAreaRead } from '../types/lab-areas'
import LabAreaFormModal from './LabAreaFormModal.vue'
import LabAreasPage from '../pages/lab-areas/index.vue'

const fake = await vi.hoisted(async () => (await import('~/testing/fakeApi')).createFakeApi())
mockNuxtImport('useApi', () => () => fake.api)

enableAutoUnmount(afterEach)

const AREA: LabAreaRead = {
  id: 'a1',
  code: 'HEM',
  name: 'Hematología',
  description: null,
  is_active: true,
  created_at: '2026-10-01T00:00:00Z',
  updated_at: '2026-10-01T00:00:00Z',
  current_manager: null
}

beforeEach(() => {
  fake.reset()
  document.body.innerHTML = ''
  fake.routes['GET /lab-areas'] = fakePage([AREA])
  fake.routes['GET /lab-areas/a1/manager-history'] = []
  fake.routes['GET /staff'] = fakePage([])
})

const VIEW = 'vladimir.lab-areas.view'

async function mountPage(tags: string[]) {
  signInWith(tags)
  const wrapper = await mountSuspended(LabAreasPage)
  await flushAll()
  return wrapper
}

async function mountModal(tags: string[], entity: LabAreaRead | null = AREA) {
  signInWith(tags)
  await mountSuspended(LabAreaFormModal, { props: { open: true, entity } })
  await flushAll()
  return document.body
}

describe('ruta y menú de lab-areas', () => {
  it('la página exige el tag view', () => {
    expect(useRouter().resolve('/lab-areas').meta.leo?.tag).toBe(VIEW)
  })

  it('el ítem "Áreas" aparece con view', async () => {
    signInWith([VIEW])
    const wrapper = await mountSuspended(DefaultLayout)
    expect(wrapper.findAll('a').find(a => a.text() === 'Áreas')?.attributes('href')).toBe('/lab-areas')
  })

  it('el ítem "Áreas" no aparece sin view, y los demás módulos siguen visibles', async () => {
    signInWith(['vladimir.lab-areas.create'])
    const wrapper = await mountSuspended(DefaultLayout)
    const labels = wrapper.findAll('a').map(a => a.text())
    expect(labels).not.toContain('Áreas')
    expect(labels).toContain('Personal')
  })

  it('la barra superior de Leo está en el layout', async () => {
    signInWith([VIEW])
    const wrapper = await mountSuspended(DefaultLayout)
    expect(wrapper.find('[data-testid="leo-current-app"]').text()).toBe('Vladimir')
  })
})

describe('listado de áreas', () => {
  it('sin create no hay botón "Nueva"; con create sí', async () => {
    expect((await mountPage([VIEW])).text()).not.toContain('Nueva')
    expect((await mountPage([VIEW, 'vladimir.lab-areas.create'])).text()).toContain('Nueva')
  })

  it('solo con view la acción de fila es "Ver"; con algún permiso de cambio, "Ver / Editar"', async () => {
    expect((await mountPage([VIEW])).text()).toMatch(/Ver(?! \/)/)
    expect((await mountPage([VIEW])).text()).not.toContain('Ver / Editar')
    expect((await mountPage([VIEW, 'vladimir.lab-areas.assign-manager'])).text()).toContain('Ver / Editar')
  })
})

describe('detalle/edición de un área', () => {
  it('el campo "Activa" exige change-status', async () => {
    expect((await mountModal([VIEW, 'vladimir.lab-areas.edit'])).textContent).not.toContain('Activa')
    expect((await mountModal([VIEW, 'vladimir.lab-areas.change-status'])).textContent).toContain('Activa')
  })

  it('el formulario de asignar encargado exige assign-manager; el historial se ve con view', async () => {
    const without = await mountModal([VIEW, 'vladimir.lab-areas.edit'])
    expect(without.textContent).toContain('Historial de encargados')
    expect(without.textContent).not.toContain('Nuevo encargado')
    document.body.innerHTML = ''
    const withTag = await mountModal([...ALL_LAB_AREAS_TAGS])
    expect(withTag.textContent).toContain('Nuevo encargado')
  })

  it('con solo view el modal es de lectura: el pie dice "Cerrar" y no hay "Guardar cambios"', async () => {
    const body = await mountModal([VIEW])
    expect(body.textContent).not.toContain('Guardar cambios')
    expect(() => button(body, 'Cerrar')).not.toThrow()
  })

  it('con edit sin change-status el PATCH no lleva is_active', async () => {
    const body = await mountModal([VIEW, 'vladimir.lab-areas.edit'])
    button(body, 'Guardar cambios').click()
    await flushAll()
    const patch = fake.requests.mock.calls.find(([method]) => method === 'PATCH')
    expect(patch?.[1]).toBe('/lab-areas/a1')
    expect(patch?.[2]).not.toHaveProperty('is_active')
    expect(patch?.[2]).toMatchObject({ code: 'HEM', name: 'Hematología' })
  })
})
