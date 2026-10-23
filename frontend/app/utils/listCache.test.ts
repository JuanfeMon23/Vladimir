import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { enableAutoUnmount, flushPromises } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { defineComponent, type UnwrapNestedRefs } from 'vue'
import { clearPaginatedListCache, usePaginatedList } from '#andromeda/composables/usePaginatedList'
import { LeoApiError } from '#leo-client/lib/errors'
import type { CacheStamp } from '#leo-client/lib/requestCache'

enableAutoUnmount(afterEach)

// Solo para la mutación (useLeoAppApi real sobre un transporte falso).
const fetchMock = vi.hoisted(() => vi.fn(async () => ({})))
mockNuxtImport('useLeoApi', () => () => fetchMock)

beforeEach(() => {
  invalidateCaches()
  clearPaginatedListCache()
})

const page = (items: string[]) => ({ items, total: items.length })

async function host(fetchPage: (p: { page: number }) => Promise<{ items: string[], total: number }>, scope: string) {
  let state!: UnwrapNestedRefs<ReturnType<typeof usePaginatedList<string, CacheStamp>>>
  await mountSuspended(defineComponent({
    setup() {
      state = reactive(usePaginatedList<string, CacheStamp>({ fetchPage, cache: listCache(scope), mapError: leoErrorMessage }))
      return () => null
    }
  }))
  await flushPromises()
  return state
}

describe('listCache + usePaginatedList', () => {
  it('volver a una página reciente sale de la caché', async () => {
    const fetchPage = vi.fn(async ({ page: p }: { page: number }) => page([`p${p}`]))
    const list = await host(fetchPage, '/t-cache')
    list.page = 2
    await flushPromises()
    list.page = 1
    await flushPromises()
    expect(fetchPage).toHaveBeenCalledTimes(2)
    expect(list.rows).toEqual(['p1'])
  })

  it('una mutación de useLeoAppApi (de cualquier recurso) invalida: volver a la página vista recarga', async () => {
    let area = 'Hematología'
    const fetchPage = vi.fn(async ({ page: p }: { page: number }) => page([`${area}-p${p}`]))
    const list = await host(fetchPage, '/t-inval')
    list.page = 2
    await flushPromises()
    area = 'Renombrada'
    await useLeoAppApi().patch('/lab-areas/1', { name: area })
    list.page = 1
    await flushPromises()
    expect(fetchPage).toHaveBeenCalledTimes(3)
    expect(list.rows).toEqual(['Renombrada-p1'])
  })

  it('una entrada vencida (TTL de 30 s) se vuelve a pedir', async () => {
    vi.useFakeTimers({ toFake: ['Date'] })
    try {
      const fetchPage = vi.fn(async ({ page: p }: { page: number }) => page([`p${p}`]))
      const list = await host(fetchPage, '/t-ttl')
      list.page = 2
      await flushPromises()
      vi.advanceTimersByTime(LIST_CACHE_TTL + 1)
      list.page = 1
      await flushPromises()
      expect(fetchPage).toHaveBeenCalledTimes(3)
    } finally {
      vi.useRealTimers()
    }
  })

  it('un error de la API se muestra legible (leoErrorMessage), no crudo', async () => {
    const err = new LeoApiError(500, 'internal', 'Traceback (most recent call last)', null)
    const rejected = Promise.reject(err)
    rejected.catch(() => {})
    const list = await host(() => rejected, '/t-error')
    expect(list.loadError).toBeTruthy()
    expect(list.loadError).not.toContain('Traceback')
  })
})
