import { vi } from 'vitest'

/**
 * `useApi` falso para tests de componentes/composables que llaman a varios
 * endpoints (solo tests; Nuxt no auto-importa `app/testing/`).
 *
 * - `routes['GET /ruta']`: respuesta (valor o función de las opciones/body).
 *   Un GET sin ruta rechaza (el test lo ve como error de carga).
 *   POST/PATCH/PUT sin ruta responden con el body recibido.
 * - `failures['PUT /ruta']`: error con el que rechaza esa llamada. El rechazo
 *   se arma fuera de `vi.fn` (Vitest 5 reporta como error del test la
 *   promesa rechazada que devuelve un mock aunque el código la capture).
 * - `requests`: spy de cada llamada `(método, ruta, body | opciones)`.
 *
 * Uso (el factory de `mockNuxtImport` se iza: el fake se crea con `vi.hoisted`):
 * ```ts
 * const fake = await vi.hoisted(async () => (await import('~/testing/fakeApi')).createFakeApi())
 * mockNuxtImport('useApi', () => () => fake.api)
 * beforeEach(() => fake.reset())
 * ```
 */
export type FakeApiMethod = 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'
export type FakeApiHandler = unknown | ((input: unknown) => unknown)

export function createFakeApi() {
  const routes: Record<string, FakeApiHandler> = {}
  const failures: Record<string, Error> = {}
  const requests = vi.fn<(method: FakeApiMethod, path: string, input?: unknown) => void>()

  function call(method: FakeApiMethod, path: string, input?: unknown): Promise<never> | Promise<unknown> {
    const key = `${method} ${path}`
    requests(method, path, input)
    const failure = failures[key]
    if (failure) return Promise.reject(failure)
    if (!(key in routes)) {
      if (method === 'GET' || method === 'DELETE') return Promise.reject(new Error(`Ruta no simulada: ${key}`))
      return Promise.resolve(input)
    }
    const handler = routes[key]
    return Promise.resolve(typeof handler === 'function' ? (handler as (input: unknown) => unknown)(input) : handler)
  }

  const api = {
    get: <T>(path: string, options?: unknown) => call('GET', path, options) as Promise<T>,
    post: <T>(path: string, body?: unknown) => call('POST', path, body) as Promise<T>,
    patch: <T>(path: string, body?: unknown) => call('PATCH', path, body) as Promise<T>,
    put: <T>(path: string, body?: unknown) => call('PUT', path, body) as Promise<T>,
    delete: <T>(path: string, options?: unknown) => call('DELETE', path, options) as Promise<T>
  }

  /** Bodies enviados con ese método a esa ruta, en orden. */
  function bodies(method: FakeApiMethod, path: string) {
    return requests.mock.calls.filter(([m, p]) => m === method && p === path).map(([, , input]) => input)
  }

  /** Limpia rutas, fallos y llamadas registradas (en `beforeEach`). */
  function reset() {
    for (const key of Object.keys(routes)) delete routes[key]
    for (const key of Object.keys(failures)) delete failures[key]
    requests.mockReset()
  }

  return { api, routes, failures, requests, bodies, reset }
}

/** Página del backend (`Page<T>`) con todos los ítems. */
export function fakePage<T>(items: T[]) {
  return { items, total: items.length, page: 1, page_size: Math.max(items.length, 1) }
}
