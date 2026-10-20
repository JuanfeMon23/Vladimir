import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mockNuxtImport } from '@nuxt/test-utils/runtime'
import { invalidateCaches } from '~/utils/requestCache'
import { ApiRequestError, useApi } from './useApi'

const fetchMock = vi.hoisted(() => vi.fn())
mockNuxtImport('useLeoApi', () => () => fetchMock)

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

async function errorOf(call: () => Promise<unknown>): Promise<ApiRequestError> {
  try {
    await call()
  } catch (err) {
    expect(err).toBeInstanceOf(ApiRequestError)
    return err as ApiRequestError
  }
  throw new Error('la llamada no falló')
}

describe('useApi', () => {
  it('envía por leo-client la ruta con el prefijo de la API y el verbo de cada método', async () => {
    fetchMock.mockResolvedValue({ ok: true })
    const api = useApi()
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
    await useApi().get('/staff', { params: { active: true } })
    expect(fetchMock.mock.calls[0]![1].query).toEqual({ active: true })
  })

  it('pasa los query params y devuelve la respuesta', async () => {
    fetchMock.mockResolvedValue({ items: [], total: 0 })
    const result = await useApi().get('/staff', { query: { page: 2, active: true } })
    expect(result).toEqual({ items: [], total: 0 })
    expect(fetchMock.mock.calls[0]![1].query).toEqual({ page: 2, active: true })
  })

  it('un AppError del backend (409) se conserva: code, message, details y status', async () => {
    failWith({ status: 409, data: { code: 'conflict', message: 'Código duplicado.', details: { code: 'HEM' } } })
    const err = await errorOf(() => useApi().post('/staff', {}))
    expect(err).toMatchObject({ code: 'conflict', message: 'Código duplicado.', details: { code: 'HEM' }, status: 409 })
  })

  it('un 403 forbidden de un tag conocido nombra el permiso faltante', async () => {
    failWith({ status: 403, data: { code: 'forbidden', message: 'No tienes permiso para realizar esta acción.', details: { action: 'vladimir.lab-areas.create' } } })
    const err = await errorOf(() => useApi().post('/lab-areas', {}))
    expect(err).toMatchObject({ code: 'forbidden', status: 403, message: 'No tienes permiso para: Crear áreas de laboratorio' })
  })

  it('un 403 forbidden de un tag desconocido conserva el mensaje del backend', async () => {
    failWith({ status: 403, data: { code: 'forbidden', message: 'No tienes permiso para realizar esta acción.', details: { action: 'vladimir.x.y' } } })
    const err = await errorOf(() => useApi().get('/x'))
    expect(err.message).toBe('No tienes permiso para realizar esta acción.')
  })

  it('un 401 de sesión conserva su código legible', async () => {
    failWith({ status: 401, data: { code: 'session_expired', message: 'Tu sesión expiró. Inicia sesión de nuevo.' } })
    const err = await errorOf(() => useApi().get('/staff'))
    expect(err).toMatchObject({ code: 'session_expired', status: 401, message: 'Tu sesión expiró. Inicia sesión de nuevo.' })
  })

  it('un 404 con AppError conserva su código', async () => {
    failWith({ status: 404, data: { code: 'not_found', message: 'No existe.' } })
    const err = await errorOf(() => useApi().get('/staff/x'))
    expect(err).toMatchObject({ code: 'not_found', status: 404 })
  })

  it('el 422 de schema de FastAPI se normaliza a request_validation con la lista en details', async () => {
    const detail = [{ loc: ['body', 'code'], msg: 'Field required', type: 'missing' }]
    failWith({ status: 422, data: { detail } })
    const err = await errorOf(() => useApi().post('/staff', {}))
    expect(err).toMatchObject({ code: 'request_validation', details: detail, status: 422 })
    expect(err.message).toMatch(/no son válidos/)
  })

  it('un detail de texto queda como http_error con ese mensaje', async () => {
    failWith({ status: 401, data: { detail: 'Not authenticated' } })
    const err = await errorOf(() => useApi().get('/staff'))
    expect(err).toMatchObject({ code: 'http_error', message: 'Not authenticated', status: 401 })
  })

  it('un 500 sin cuerpo da un mensaje legible (no el statusText técnico)', async () => {
    failWith({ status: 500, statusText: 'Internal Server Error', data: undefined })
    const err = await errorOf(() => useApi().get('/staff'))
    expect(err).toMatchObject({ code: 'unknown_error', status: 500 })
    expect(err.message).not.toMatch(/Internal Server Error/)
    expect(err.message).toMatch(/servidor/i)
  })

  it('un 500 sin cuerpo ni statusText usa un mensaje genérico', async () => {
    failWith({ status: 500, data: null })
    const err = await errorOf(() => useApi().get('/staff'))
    expect(err.code).toBe('unknown_error')
    expect(err.message).not.toBe('')
  })

  it('un error de red (sin respuesta) es network_error sin status', async () => {
    failWith(new TypeError('Failed to fetch'))
    const err = await errorOf(() => useApi().get('/staff'))
    expect(err).toMatchObject({ code: 'network_error', status: undefined })
  })

  describe('caché de lecturas (cacheTtl) e invalidación', () => {
    it('sin cacheTtl cada GET llega al servidor', async () => {
      fetchMock.mockResolvedValue({ items: [] })
      await useApi().get('/units')
      await useApi().get('/units')
      expect(fetchMock).toHaveBeenCalledTimes(2)
    })

    it('con cacheTtl el mismo GET (ruta + parámetros) se sirve de la caché', async () => {
      fetchMock.mockResolvedValue({ items: ['a'] })
      const first = await useApi().get('/units', { params: { page_size: 200 }, cacheTtl: 60_000 })
      const second = await useApi().get('/units', { params: { page_size: 200 }, cacheTtl: 60_000 })
      expect(second).toEqual(first)
      expect(fetchMock).toHaveBeenCalledTimes(1)
    })

    it('parámetros distintos no comparten entrada', async () => {
      fetchMock.mockResolvedValue({ items: [] })
      await useApi().get('/units', { params: { page_size: 200 }, cacheTtl: 60_000 })
      await useApi().get('/units', { params: { page_size: 100 }, cacheTtl: 60_000 })
      expect(fetchMock).toHaveBeenCalledTimes(2)
    })

    it('cacheTtl no viaja al solicitante de leo-client', async () => {
      fetchMock.mockResolvedValue({})
      await useApi().get('/units', { cacheTtl: 1000 })
      expect(fetchMock.mock.calls[0]![1]).not.toHaveProperty('cacheTtl')
    })

    it.each(['post', 'patch', 'put'] as const)('un %s exitoso invalida las lecturas del recurso', async (verb) => {
      fetchMock.mockResolvedValue({ items: [] })
      await useApi().get('/units', { cacheTtl: 60_000 })
      await useApi()[verb]('/units/3', { name: 'x' })
      await useApi().get('/units', { cacheTtl: 60_000 })
      expect(fetchMock.mock.calls.filter(([, o]) => o.method === 'GET')).toHaveLength(2)
    })

    it('una mutación de OTRO recurso también invalida (no se adivina qué recursos la muestran)', async () => {
      fetchMock.mockResolvedValue({ items: [] })
      await useApi().get('/units', { cacheTtl: 60_000 })
      await useApi().post('/staff', {})
      await useApi().get('/units', { cacheTtl: 60_000 })
      expect(fetchMock.mock.calls.filter(([, o]) => o.method === 'GET')).toHaveLength(2)
    })

    it('una mutación fallida no invalida', async () => {
      fetchMock.mockResolvedValueOnce({ items: [] })
      await useApi().get('/units', { cacheTtl: 60_000 })
      failWith({ status: 409, data: { code: 'conflict', message: 'dup' } })
      await errorOf(() => useApi().post('/units', {}))
      fetchMock.mockReset()
      fetchMock.mockResolvedValue({ items: [] })
      await useApi().get('/units', { cacheTtl: 60_000 })
      expect(fetchMock).not.toHaveBeenCalled()
    })

    it('un GET fallido no se guarda en la caché', async () => {
      failWith({ status: 500, data: null })
      await errorOf(() => useApi().get('/units', { cacheTtl: 60_000 }))
      fetchMock.mockReset()
      fetchMock.mockResolvedValue({ items: ['ok'] })
      expect(await useApi().get('/units', { cacheTtl: 60_000 })).toEqual({ items: ['ok'] })
    })
  })
})
