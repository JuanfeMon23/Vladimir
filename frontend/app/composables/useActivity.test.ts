import { mockNuxtImport } from '@nuxt/test-utils/runtime'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick, ref } from 'vue'
import { ApiRequestError } from './useApi'
import { useActivity } from './useActivity'

// El fallo se simula fuera de `vi.fn`: Vitest 5 reporta como error del test
// la promesa rechazada que devuelve un mock aunque el código la capture.
const { getMock, state } = vi.hoisted(() => ({ getMock: vi.fn(), state: { failWith: null as Error | null } }))
mockNuxtImport('useApi', () => () => ({
  get: (...args: unknown[]) => (state.failWith ? Promise.reject(state.failWith) : getMock(...args))
}))

function event(id: string, action: 'activated' | 'deactivated' = 'deactivated') {
  return { id, entity_type: 'units', entity_id: 'u1', action, reason: null, occurred_at: '2026-10-02T10:00:00Z' }
}

const flush = async () => {
  for (let i = 0; i < 4; i++) await nextTick()
  await new Promise(resolve => setTimeout(resolve, 0))
}

describe('useActivity', () => {
  beforeEach(() => {
    getMock.mockReset()
    state.failWith = null
  })

  it('carga la primera página del historial de la entidad', async () => {
    getMock.mockResolvedValue({ items: [event('e1')], total: 1, page: 1, page_size: 20 })
    const activity = useActivity('units', 'u1')
    await flush()
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
    const activity = useActivity('units', 'u1', { pageSize: 1 })
    await flush()
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
    const activity = useActivity('staff', id)
    await flush()
    expect(getMock).not.toHaveBeenCalled()
    expect(activity.events).toEqual([])
    id.value = 's1'
    await flush()
    expect(getMock).toHaveBeenCalledTimes(1)
  })

  it('un error deja el mensaje del backend', async () => {
    state.failWith = new ApiRequestError({ code: 'not_found', message: 'No existe.' }, 404)
    const activity = useActivity('units', 'u1')
    await flush()
    expect(activity.error).toBe('No existe.')
    expect(activity.loading).toBe(false)
  })
})
