import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { mockNuxtImport } from '@nuxt/test-utils/runtime'
import { LeoApiError } from '#leo-client/lib/errors'
import { PERMISSION_NAMES } from '~/utils/permissionNames'

const fetchMock = vi.hoisted(() => vi.fn())
mockNuxtImport('useLeoApi', () => () => fetchMock)

beforeAll(() => registerPermissionNames(PERMISSION_NAMES))
beforeEach(() => {
  fetchMock.mockReset()
  invalidateCaches()
})

/** Rechaza fuera de `vi.fn` (Vitest 5 reporta como error el rechazo de un mock). */
function failWith(err: unknown) {
  const rejected = Promise.reject(err)
  rejected.catch(() => {})
  fetchMock.mockImplementation(() => rejected)
}

async function errorOf(call: () => Promise<unknown>): Promise<LeoApiError> {
  try {
    await call()
  } catch (err) {
    expect(err).toBeInstanceOf(LeoApiError)
    return err as LeoApiError
  }
  throw new Error('la llamada no falló')
}

describe('useLeoAppApi (con la configuración de Vladimir)', () => {
  it('envía por leo-client la ruta con el prefijo de la API y el verbo de cada método', async () => {
    fetchMock.mockResolvedValue({ ok: true })
    const api = useLeoAppApi()
    await api.get('/staff')
    await api.post('/staff', { a: 1 })
    await api.patch('/staff/1', { a: 2 })
    await api.put('/staff/1', { a: 3 })
    await api.delete('/staff/1')
    const calls = fetchMock.mock.calls.map(([path, opts]) => [path, opts.method, opts.body])
    expect(calls).toEqual([
      ['/api/v1/staff', 'GET', undefined],
      ['/api/v1/staff', 'POST', { a: 1 }],
      ['/api/v1/staff/1', 'PATCH', { a: 2 }],
      ['/api/v1/staff/1', 'PUT', { a: 3 }],
      ['/api/v1/staff/1', 'DELETE', undefined]
    ])
  })

  it('`params` se envía como query', async () => {
    fetchMock.mockResolvedValue({})
    await useLeoAppApi().get('/staff', { params: { active: true } })
    expect(fetchMock.mock.calls[0]![1].query).toEqual({ active: true })
  })

  it('pasa los query params y devuelve la respuesta', async () => {
    fetchMock.mockResolvedValue({ items: [], total: 0 })
    const result = await useLeoAppApi().get('/staff', { query: { page: 2, active: true } })
    expect(result).toEqual({ items: [], total: 0 })
    expect(fetchMock.mock.calls[0]![1].query).toEqual({ page: 2, active: true })
  })

  it('un AppError del backend (409) se conserva: code, message, details y status', async () => {
    failWith(new LeoApiError(409, 'conflict', 'Código duplicado.', { code: 'HEM' }))
    const err = await errorOf(() => useLeoAppApi().post('/staff', {}))
    expect(err).toMatchObject({ code: 'conflict', message: 'Código duplicado.', details: { code: 'HEM' }, status: 409 })
  })

  it('un 403 forbidden de un tag conocido nombra el permiso faltante', async () => {
    failWith(new LeoApiError(403, 'forbidden', 'No tienes permiso para realizar esta acción.', { action: 'vladimir.lab-areas.create' }))
    const err = await errorOf(() => useLeoAppApi().post('/lab-areas', {}))
    expect(err).toMatchObject({ code: 'forbidden', status: 403, message: 'No tienes permiso para: Crear áreas de laboratorio' })
  })

  it('un 403 forbidden de un tag desconocido conserva el mensaje del backend', async () => {
    failWith(new LeoApiError(403, 'forbidden', 'No tienes permiso para realizar esta acción.', { action: 'vladimir.x.y' }))
    const err = await errorOf(() => useLeoAppApi().get('/x'))
    expect(err.message).toBe('No tienes permiso para realizar esta acción.')
  })

  describe('caché de lecturas (cacheTtl) e invalidación', () => {
    it('sin cacheTtl cada GET llega al servidor', async () => {
      fetchMock.mockResolvedValue({ items: [] })
      await useLeoAppApi().get('/units')
      await useLeoAppApi().get('/units')
      expect(fetchMock).toHaveBeenCalledTimes(2)
    })

    it('con cacheTtl el mismo GET (ruta + parámetros) se sirve de la caché', async () => {
      fetchMock.mockResolvedValue({ items: ['a'] })
      const first = await useLeoAppApi().get('/units', { params: { page_size: 200 }, cacheTtl: 60_000 })
      const second = await useLeoAppApi().get('/units', { params: { page_size: 200 }, cacheTtl: 60_000 })
      expect(second).toEqual(first)
      expect(fetchMock).toHaveBeenCalledTimes(1)
    })

    it('parámetros distintos no comparten entrada', async () => {
      fetchMock.mockResolvedValue({ items: [] })
      await useLeoAppApi().get('/units', { params: { page_size: 200 }, cacheTtl: 60_000 })
      await useLeoAppApi().get('/units', { params: { page_size: 100 }, cacheTtl: 60_000 })
      expect(fetchMock).toHaveBeenCalledTimes(2)
    })

    it('cacheTtl no viaja al solicitante de leo-client', async () => {
      fetchMock.mockResolvedValue({})
      await useLeoAppApi().get('/units', { cacheTtl: 1000 })
      expect(fetchMock.mock.calls[0]![1]).not.toHaveProperty('cacheTtl')
    })

    it.each(['post', 'patch', 'put'] as const)('un %s exitoso invalida las lecturas del recurso', async (verb) => {
      fetchMock.mockResolvedValue({ items: [] })
      await useLeoAppApi().get('/units', { cacheTtl: 60_000 })
      await useLeoAppApi()[verb]('/units/3', { name: 'x' })
      await useLeoAppApi().get('/units', { cacheTtl: 60_000 })
      expect(fetchMock.mock.calls.filter(([, o]) => o.method === 'GET')).toHaveLength(2)
    })

    it('una mutación de OTRO recurso también invalida (no se adivina qué recursos la muestran)', async () => {
      fetchMock.mockResolvedValue({ items: [] })
      await useLeoAppApi().get('/units', { cacheTtl: 60_000 })
      await useLeoAppApi().post('/staff', {})
      await useLeoAppApi().get('/units', { cacheTtl: 60_000 })
      expect(fetchMock.mock.calls.filter(([, o]) => o.method === 'GET')).toHaveLength(2)
    })

    it('una mutación fallida no invalida', async () => {
      fetchMock.mockResolvedValueOnce({ items: [] })
      await useLeoAppApi().get('/units', { cacheTtl: 60_000 })
      failWith(new LeoApiError(409, 'conflict', 'dup'))
      await errorOf(() => useLeoAppApi().post('/units', {}))
      fetchMock.mockReset()
      fetchMock.mockResolvedValue({ items: [] })
      await useLeoAppApi().get('/units', { cacheTtl: 60_000 })
      expect(fetchMock).not.toHaveBeenCalled()
    })

    it('un GET fallido no se guarda en la caché', async () => {
      failWith(new LeoApiError(500, 'http_error', ''))
      await errorOf(() => useLeoAppApi().get('/units', { cacheTtl: 60_000 }))
      fetchMock.mockReset()
      fetchMock.mockResolvedValue({ items: ['ok'] })
      expect(await useLeoAppApi().get('/units', { cacheTtl: 60_000 })).toEqual({ items: ['ok'] })
    })
  })
})
