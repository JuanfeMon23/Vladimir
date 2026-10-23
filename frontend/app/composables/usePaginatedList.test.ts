import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { enableAutoUnmount, flushPromises } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { defineComponent, type UnwrapNestedRefs } from 'vue'
import type { Page } from '~/types/api'
import { signInWith } from '#leo-client/testing/session'
import { apiError } from '~/testing/apiError'
import { usePaginatedList } from './usePaginatedList'

// Un host sin desmontar compartiría la carga de su clave con el siguiente test.
enableAutoUnmount(afterEach)

// Solo para la mutación del test de invalidación entre recursos.
const fetchMock = vi.hoisted(() => vi.fn(async () => ({})))
mockNuxtImport('useLeoApi', () => () => fetchMock)

beforeEach(() => {
  // La navegación pasa por el middleware de leo-client: requiere sesión.
  signInWith([])
  invalidateCaches()
  clearNuxtData()
})

/** Consulta de la URL actual; la navegación de `router.replace` termina en un macrotask. */
const urlQuery = () => useRouter().currentRoute.value.query

type Fetch = Parameters<typeof usePaginatedList<string>>[0]

function page(items: string[], total = items.length): Page<string> {
  return { items, total, page: 1, page_size: 20 }
}

function rejected(err: unknown): Promise<never> {
  const p = Promise.reject(err)
  p.catch(() => {})
  return p
}

/** Monta un host (necesario por `onMounted`) y devuelve el estado del composable. */
async function host(fetchPage: Fetch, options: Parameters<typeof usePaginatedList<string>>[1] = {}, route = '/') {
  let state!: UnwrapNestedRefs<ReturnType<typeof usePaginatedList<string>>>
  await mountSuspended(defineComponent({
    setup() {
      state = reactive(usePaginatedList(fetchPage, options))
      return () => null
    }
  }), { route })
  await flushPromises()
  return state
}

function deferred<T>() {
  let resolve!: (v: T) => void
  const promise = new Promise<T>((r) => { resolve = r })
  return { promise, resolve }
}

describe('usePaginatedList', () => {
  it('carga la página 1 al montar con el tamaño por defecto (20)', async () => {
    const fetchPage = vi.fn<Fetch>(async () => page(['a', 'b'], 42))
    const list = await host(fetchPage)
    expect(fetchPage).toHaveBeenCalledTimes(1)
    expect(fetchPage).toHaveBeenCalledWith({ page: 1, page_size: 20 })
    expect(list.rows).toEqual(['a', 'b'])
    expect(list.total).toBe(42)
    expect(list.loading).toBe(false)
    expect(list.loadError).toBeNull()
  })

  it('immediate: false no carga hasta reload()', async () => {
    const fetchPage = vi.fn<Fetch>(async () => page(['a']))
    const list = await host(fetchPage, { immediate: false, pageSize: 5 })
    expect(fetchPage).not.toHaveBeenCalled()
    await list.reload()
    expect(fetchPage).toHaveBeenCalledWith({ page: 1, page_size: 5 })
  })

  it('loading es true mientras carga', async () => {
    const d = deferred<Page<string>>()
    const list = await host(() => d.promise)
    expect(list.loading).toBe(true)
    d.resolve(page(['a']))
    await flushPromises()
    expect(list.loading).toBe(false)
    expect(list.rows).toEqual(['a'])
  })

  it('cambiar de página recarga con esa página', async () => {
    const fetchPage = vi.fn<Fetch>(async ({ page: p }) => page([`fila-${p}`]))
    const list = await host(fetchPage)
    list.page = 3
    await flushPromises()
    expect(fetchPage).toHaveBeenLastCalledWith({ page: 3, page_size: 20 })
    expect(list.rows).toEqual(['fila-3'])
  })

  it('cambiar un filtro desde la página 1 recarga una vez', async () => {
    const filter = ref<boolean | undefined>()
    const fetchPage = vi.fn<Fetch>(async () => page(['a']))
    await host(fetchPage, { filters: [filter] })
    filter.value = true
    await flushPromises()
    expect(fetchPage).toHaveBeenCalledTimes(2)
  })

  it('cambiar un filtro desde otra página vuelve a la 1 y recarga una sola vez', async () => {
    const filter = ref('x')
    const fetchPage = vi.fn<Fetch>(async () => page(['a']))
    const list = await host(fetchPage, { filters: [filter] })
    list.page = 4
    await flushPromises()
    fetchPage.mockClear()
    filter.value = 'y'
    await flushPromises()
    expect(list.page).toBe(1)
    expect(fetchPage).toHaveBeenCalledTimes(1)
    expect(fetchPage).toHaveBeenCalledWith({ page: 1, page_size: 20 })
  })

  it('el fetchPage lee el filtro vigente (p. ej. active / include_inactive)', async () => {
    const active = ref<boolean | undefined>()
    const calls: Array<boolean | undefined> = []
    const list = await host(async () => { calls.push(active.value); return page([]) }, { filters: [active] })
    active.value = false
    await flushPromises()
    expect(calls).toEqual([undefined, false])
    expect(list.rows).toEqual([])
  })

  it('un error con mensaje queda en loadError y loading vuelve a false', async () => {
    const failure = apiError({ code: 'x', message: 'Fallo del servidor.' }, 500)
    const list = await host(() => rejected(failure))
    expect(list.loadError).toBe('Fallo del servidor.')
    expect(list.loading).toBe(false)
  })

  it('un error sin mensaje usa errorMessage y luego un genérico', async () => {
    const list = await host(() => rejected('boom'), { errorMessage: 'No se pudo cargar el personal.' })
    expect(list.loadError).toBe('No se pudo cargar el personal.')
    const generic = await host(() => rejected('boom'))
    expect(generic.loadError).toBe('No se pudo cargar el listado.')
  })

  it('una recarga exitosa limpia el loadError anterior', async () => {
    let fail = true
    const list = await host(() => (fail ? rejected(new Error('mal')) : Promise.resolve(page(['ok']))))
    expect(list.loadError).toBe('mal')
    fail = false
    await list.reload()
    expect(list.loadError).toBeNull()
    expect(list.rows).toEqual(['ok'])
  })

  it('ignora la respuesta de una petición vieja que termina después de la nueva', async () => {
    const first = deferred<Page<string>>()
    const second = deferred<Page<string>>()
    const queue = [first, second]
    const list = await host(() => queue.shift()!.promise)
    const reloading = list.reload()
    second.resolve(page(['nueva']))
    await reloading
    first.resolve(page(['vieja']))
    await flushPromises()
    expect(list.rows).toEqual(['nueva'])
    expect(list.loading).toBe(false)
  })
})

describe('usePaginatedList: búsqueda (search)', () => {
  it('envía q normalizado (recortado) junto a la paginación', async () => {
    const search = ref('')
    const fetchPage = vi.fn<Fetch>(async () => page([]))
    await host(fetchPage, { search })
    search.value = '  herrera  '
    await flushPromises()
    expect(fetchPage).toHaveBeenLastCalledWith({ page: 1, page_size: 20, q: 'herrera' })
  })

  it('sin texto no envía q (ni en la primera carga)', async () => {
    const search = ref('   ')
    const fetchPage = vi.fn<Fetch>(async () => page([]))
    await host(fetchPage, { search })
    expect(fetchPage).toHaveBeenCalledWith({ page: 1, page_size: 20 })
    expect(fetchPage.mock.calls[0]![0]).not.toHaveProperty('q')
  })

  it('al cambiar el término desde otra página vuelve a la 1 y recarga una sola vez', async () => {
    const search = ref('')
    const fetchPage = vi.fn<Fetch>(async () => page(['a']))
    const list = await host(fetchPage, { search })
    list.page = 3
    await flushPromises()
    fetchPage.mockClear()
    search.value = 'hemo'
    await flushPromises()
    expect(list.page).toBe(1)
    expect(fetchPage).toHaveBeenCalledTimes(1)
    expect(fetchPage).toHaveBeenCalledWith({ page: 1, page_size: 20, q: 'hemo' })
  })

  it('no repite la petición si el término normalizado no cambió', async () => {
    const search = ref('hemo')
    const fetchPage = vi.fn<Fetch>(async () => page(['a']))
    await host(fetchPage, { search })
    fetchPage.mockClear()
    search.value = '  hemo '
    await flushPromises()
    expect(fetchPage).not.toHaveBeenCalled()
  })

  it('expone searchTerm normalizado para el estado vacío', async () => {
    const search = ref('')
    const list = await host(async () => page([]), { search })
    expect(list.searchTerm).toBe('')
    search.value = ' mg  dl '
    await flushPromises()
    expect(list.searchTerm).toBe('mg dl')
  })

  it('conserva las filas anteriores mientras busca (loading en true)', async () => {
    const search = ref('')
    const second = deferred<Page<string>>()
    const queue: Array<Promise<Page<string>>> = [Promise.resolve(page(['previa'])), second.promise]
    const list = await host(() => queue.shift()!, { search })
    search.value = 'x'
    await flushPromises()
    expect(list.loading).toBe(true)
    expect(list.rows).toEqual(['previa'])
    second.resolve(page(['nueva']))
    await flushPromises()
    expect(list.rows).toEqual(['nueva'])
    expect(list.loading).toBe(false)
  })

  it('ignora la respuesta de una búsqueda vieja que llega después de la nueva', async () => {
    const search = ref('')
    const old = deferred<Page<string>>()
    const fresh = deferred<Page<string>>()
    const queue: Array<Promise<Page<string>>> = [Promise.resolve(page([])), old.promise, fresh.promise]
    const list = await host(() => queue.shift()!, { search })
    search.value = 'a'
    await flushPromises()
    search.value = 'ab'
    await flushPromises()
    fresh.resolve(page(['ab']))
    await flushPromises()
    old.resolve(page(['a']))
    await flushPromises()
    expect(list.rows).toEqual(['ab'])
  })

  it('sincroniza q y page con la URL (replace) y los quita al volver al estado base', async () => {
    const search = ref('')
    const list = await host(async () => page([]), { search })
    search.value = 'herrera'
    await vi.waitFor(() => expect(urlQuery()).toEqual({ q: 'herrera' }))
    list.page = 2
    await vi.waitFor(() => expect(urlQuery()).toEqual({ q: 'herrera', page: '2' }))
    search.value = ''
    await vi.waitFor(() => expect(urlQuery()).toEqual({}))
  })

  it('conserva otros parámetros de la URL al sincronizar', async () => {
    const search = ref('')
    await host(async () => page([]), { search }, '/?otro=x')
    search.value = 'a'
    await vi.waitFor(() => expect(urlQuery()).toEqual({ otro: 'x', q: 'a' }))
  })

  it('arranca con q y page de la URL (compartir un enlace)', async () => {
    const search = ref('')
    const fetchPage = vi.fn<Fetch>(async () => page([]))
    const list = await host(fetchPage, { search }, '/?q=hemograma&page=3')
    expect(search.value).toBe('hemograma')
    expect(list.page).toBe(3)
    expect(fetchPage).toHaveBeenCalledTimes(1)
    expect(fetchPage).toHaveBeenCalledWith({ page: 3, page_size: 20, q: 'hemograma' })
  })

  it('una page inválida en la URL se toma como 1', async () => {
    const list = await host(async () => page([]), { search: ref('') }, '/?page=abc')
    expect(list.page).toBe(1)
  })

  it('urlSync: false no toca la URL', async () => {
    const search = ref('')
    await host(async () => page([]), { search, urlSync: false })
    search.value = 'zzz'
    await flushPromises()
    await new Promise(resolve => setTimeout(resolve, 30))
    expect(urlQuery()).toEqual({})
  })
})

describe('usePaginatedList: carga inicial y caché (resource)', () => {
  it('con resource carga una vez al montar (useAsyncData) y llena filas y total', async () => {
    const fetchPage = vi.fn<Fetch>(async () => page(['a', 'b'], 9))
    const list = await host(fetchPage, { resource: '/t-inicial' })
    expect(fetchPage).toHaveBeenCalledTimes(1)
    expect(list.rows).toEqual(['a', 'b'])
    expect(list.total).toBe(9)
    expect(list.loading).toBe(false)
  })

  it('un error en la carga inicial queda en loadError', async () => {
    const list = await host(() => rejected(new Error('sin backend')), { resource: '/t-error' })
    expect(list.loadError).toBe('sin backend')
    expect(list.loading).toBe(false)
  })

  it('volver a una página reciente sale de la caché (sin nueva petición)', async () => {
    const fetchPage = vi.fn<Fetch>(async ({ page: p }) => page([`p${p}`]))
    const list = await host(fetchPage, { resource: '/t-cache' })
    list.page = 2
    await flushPromises()
    list.page = 1
    await flushPromises()
    expect(fetchPage).toHaveBeenCalledTimes(2)
    expect(list.rows).toEqual(['p1'])
  })

  it('volver a una búsqueda reciente sale de la caché', async () => {
    const search = ref('')
    const fetchPage = vi.fn<Fetch>(async ({ q }) => page([q ?? 'todo']))
    const list = await host(fetchPage, { resource: '/t-cache-q', search })
    search.value = 'abc'
    await flushPromises()
    search.value = ''
    await flushPromises()
    expect(fetchPage).toHaveBeenCalledTimes(2)
    expect(list.rows).toEqual(['todo'])
  })

  it('los filtros forman parte de la clave de caché', async () => {
    const active = ref<boolean | undefined>()
    const fetchPage = vi.fn<Fetch>(async () => page([String(active.value)]))
    const list = await host(fetchPage, { resource: '/t-cache-f', filters: [active] })
    active.value = true
    await flushPromises()
    expect(list.rows).toEqual(['true'])
    active.value = undefined
    await flushPromises()
    expect(list.rows).toEqual(['undefined'])
    expect(fetchPage).toHaveBeenCalledTimes(2)
  })

  it('reload() siempre refresca (ignora la caché)', async () => {
    const fetchPage = vi.fn<Fetch>(async () => page(['x']))
    const list = await host(fetchPage, { resource: '/t-reload' })
    await list.reload()
    expect(fetchPage).toHaveBeenCalledTimes(2)
  })

  it('una mutación invalida: volver a la página ya vista recarga', async () => {
    const fetchPage = vi.fn<Fetch>(async ({ page: p }) => page([`p${p}`]))
    const list = await host(fetchPage, { resource: '/t-inval' })
    list.page = 2
    await flushPromises()
    invalidateCaches()
    list.page = 1
    await flushPromises()
    expect(fetchPage).toHaveBeenCalledTimes(3)
  })

  it('una entrada vencida (TTL) se vuelve a pedir', async () => {
    vi.useFakeTimers({ toFake: ['Date'] })
    try {
      const fetchPage = vi.fn<Fetch>(async ({ page: p }) => page([`p${p}`]))
      const list = await host(fetchPage, { resource: '/t-ttl', cacheTtl: 1000 })
      list.page = 2
      await flushPromises()
      vi.advanceTimersByTime(1001)
      list.page = 1
      await flushPromises()
      expect(fetchPage).toHaveBeenCalledTimes(3)
    } finally {
      vi.useRealTimers()
    }
  })
})

describe('usePaginatedList: invalidación entre recursos', () => {
  it('una mutación de OTRO recurso refresca el listado que lo muestra al volver a una página ya vista', async () => {
    let areaName = 'Hematología'
    const fetchPage = vi.fn<Fetch>(async ({ page: p }) => page([`${areaName}-p${p}`]))
    const list = await host(fetchPage, { resource: '/t-cross' })
    list.page = 2
    await flushPromises()
    // Renombrar un área (otro recurso) con el useLeoAppApi real: invalida todo.
    areaName = 'Hematología renombrada'
    await useLeoAppApi().patch('/lab-areas/1', { name: areaName })
    list.page = 1
    await flushPromises()
    expect(list.rows).toEqual(['Hematología renombrada-p1'])
  })
})
