import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fakePage } from '~/testing/fakeApi'
import { signInWith } from '~/testing/session'
import { button, click, flushAll, setValue } from '~/testing/dom'
import type { StaffRead } from '../../types/staff'
import StaffIndex from './index.vue'

const fake = await vi.hoisted(async () => (await import('~/testing/fakeApi')).createFakeApi())
mockNuxtImport('useApi', () => () => fake.api)

enableAutoUnmount(afterEach)

function person(id: string, first_name: string, last_name: string): StaffRead {
  return {
    id, first_name, last_name, document_type: 'CC', document_number: `doc-${id}`, job_title: 'Bacterióloga',
    is_active: true, created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z'
  }
}

const everyone = [person('1', 'Ana', 'Herrera'), person('2', 'Luis', 'Pérez')]

beforeEach(() => {
  // La navegación pasa por el middleware de leo-client: requiere sesión.
  signInWith([])
  fake.reset()
  invalidateCaches()
  clearNuxtData()
  fake.routes['GET /staff'] = (options: unknown) => {
    const q = (options as { params?: { q?: string } }).params?.q
    return fakePage(q ? everyone.filter(p => p.last_name.toLowerCase().includes(q.toLowerCase())) : everyone)
  }
})

const queriesSent = () => fake.requests.mock.calls.map(([, , options]) => (options as { params: { q?: string } }).params.q)
/** El input del buscador (el wrapper no está en el documento: se busca por rol). */
const searchBox = (root: Element) => root.querySelector<HTMLInputElement>('[role="search"] input')!

describe('listado de personal: búsqueda', () => {
  it('carga la página 1 sin q y muestra a todos', async () => {
    const wrapper = await mountSuspended(StaffIndex, { route: '/staff' })
    await flushAll()
    expect(wrapper.text()).toContain('Herrera')
    expect(wrapper.text()).toContain('Pérez')
    expect(queriesSent()).toEqual([undefined])
  })

  it('buscar envía q con el texto y muestra solo las coincidencias', async () => {
    const wrapper = await mountSuspended(StaffIndex, { route: '/staff' })
    await flushAll()
    await setValue(searchBox(wrapper.element), 'herrera')
    await vi.waitFor(() => expect(queriesSent()).toEqual([undefined, 'herrera']), { timeout: 2000 })
    await flushAll()
    expect(wrapper.text()).toContain('Herrera')
    expect(wrapper.text()).not.toContain('Pérez')
  })

  it('sin coincidencias muestra "Sin resultados" y Limpiar búsqueda restaura el listado', async () => {
    const wrapper = await mountSuspended(StaffIndex, { route: '/staff' })
    await flushAll()
    await setValue(searchBox(wrapper.element), 'zzz')
    await vi.waitFor(() => expect(wrapper.text()).toContain('Sin resultados para «zzz»'), { timeout: 2000 })
    expect(wrapper.text()).not.toContain('No hay personal registrado.')
    await click(button(wrapper.element, 'Limpiar búsqueda'))
    await vi.waitFor(() => expect(wrapper.text()).toContain('Pérez'), { timeout: 2000 })
    expect(searchBox(wrapper.element).value).toBe('')
  })

  it('abre con ?q= de la URL: el input y la petición ya llevan el término', async () => {
    const wrapper = await mountSuspended(StaffIndex, { route: '/staff?q=herrera' })
    await flushAll()
    expect(searchBox(wrapper.element).value).toBe('herrera')
    expect(queriesSent()).toEqual(['herrera'])
    expect(wrapper.text()).not.toContain('Pérez')
  })

  it('sin personal y sin búsqueda mantiene el vacío "No hay personal registrado."', async () => {
    fake.routes['GET /staff'] = fakePage([])
    const wrapper = await mountSuspended(StaffIndex, { route: '/staff' })
    await flushAll()
    expect(wrapper.text()).toContain('No hay personal registrado.')
    expect(wrapper.text()).not.toContain('Sin resultados')
  })
})
