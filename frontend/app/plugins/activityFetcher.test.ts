import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, nextTick, ref } from 'vue'
import { useActivity } from '#andromeda/composables/useActivity'
import { apiError } from '~/testing/apiError'

// Cubre el `ActivityFetcher` que provee el plugin `activityFetcher` a `useActivity` de Andromeda.
// El fallo se simula fuera de `vi.fn`: Vitest 5 reporta como error del test
// la promesa rechazada que devuelve un mock aunque el código la capture.
const { getMock, state } = vi.hoisted(() => ({ getMock: vi.fn(), state: { failWith: null as Error | null } }))
mockNuxtImport('useLeoAppApi', () => () => ({
  get: (...args: unknown[]) => (state.failWith ? Promise.reject(state.failWith) : getMock(...args))
}))

enableAutoUnmount(afterEach)

function event(id: string, action: 'activated' | 'deactivated' = 'deactivated') {
  return { id, entity_type: 'units', entity_id: 'u1', action, reason: null, occurred_at: '2026-10-02T10:00:00Z' }
}

const flush = async () => {
  for (let i = 0; i < 4; i++) await nextTick()
  await new Promise(resolve => setTimeout(resolve, 0))
}

/** Monta un host (el fetcher se inyecta desde la app) y devuelve el estado del composable. */
async function host(entityId: string | null | ReturnType<typeof ref<string | null>>, options: Parameters<typeof useActivity>[2] = {}) {
  let activity!: ReturnType<typeof useActivity>
  await mountSuspended(defineComponent({
    setup() {
      activity = useActivity('units', entityId as never, options)
      return () => h('div')
    }
  }))
  await flush()
  return activity
}

describe('plugin activityFetcher + useActivity', () => {
  beforeEach(() => {
    getMock.mockReset()
    state.failWith = null
  })

  it('carga la primera página del historial de la entidad', async () => {
    getMock.mockResolvedValue({ items: [event('e1')], total: 1, page: 1, page_size: 20 })
    const activity = await host('u1')
    expect(getMock).toHaveBeenCalledWith('/activity', {
      params: { entity_type: 'units', entity_id: 'u1', page: 1, page_size: 20 }
    })
    expect(activity.events.map(e => e.id)).toEqual(['e1'])
    expect(activity.total).toBe(1)
    expect(activity.hasMore).toBe(false)
    expect(activity.loading).toBe(false)
  })

  it('loadMore() agrega la página siguiente', async () => {
    getMock
      .mockResolvedValueOnce({ items: [event('e1')], total: 2, page: 1, page_size: 1 })
      .mockResolvedValueOnce({ items: [event('e2', 'activated')], total: 2, page: 2, page_size: 1 })
    const activity = await host('u1', { pageSize: 1 })
    expect(activity.hasMore).toBe(true)
    await activity.loadMore()
    expect(getMock).toHaveBeenLastCalledWith('/activity', {
      params: { entity_type: 'units', entity_id: 'u1', page: 2, page_size: 1 }
    })
    expect(activity.events.map(e => e.id)).toEqual(['e1', 'e2'])
    expect(activity.hasMore).toBe(false)
  })

  it('sin id no consulta y al recibir uno carga', async () => {
    getMock.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 })
    const id = ref<string | null>(null)
    const activity = await host(id)
    expect(getMock).not.toHaveBeenCalled()
    expect(activity.events).toEqual([])
    id.value = 's1'
    await flush()
    expect(getMock).toHaveBeenCalledTimes(1)
  })

  it('un error deja el mensaje legible del backend', async () => {
    state.failWith = apiError({ code: 'not_found', message: 'No existe.' }, 404)
    const activity = await host('u1')
    expect(activity.error).toBe('No existe.')
    expect(activity.loading).toBe(false)
  })

  it('un error de red no muestra el texto crudo', async () => {
    state.failWith = new TypeError('Failed to fetch')
    const activity = await host('u1')
    expect(activity.error).not.toContain('Failed to fetch')
    expect(activity.error).toBeTruthy()
  })
})
