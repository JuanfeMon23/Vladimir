import { afterEach, describe, expect, it, vi } from 'vitest'
import { cacheKey, cachedRequest, invalidateCaches, isCacheFresh, stampCache } from './requestCache'

afterEach(() => vi.useRealTimers())

describe('cacheKey', () => {
  it('es determinista: no depende del orden de las claves', () => {
    expect(cacheKey('/staff', { page: 1, q: 'a' })).toBe(cacheKey('/staff', { q: 'a', page: 1 }))
  })

  it('ignora parámetros undefined, null y vacíos', () => {
    expect(cacheKey('/staff', { page: 1, q: '', active: undefined, x: null })).toBe(cacheKey('/staff', { page: 1 }))
  })

  it('distingue recursos y parámetros', () => {
    expect(cacheKey('/staff', { page: 1 })).not.toBe(cacheKey('/staff', { page: 2 }))
    expect(cacheKey('/staff', { page: 1 })).not.toBe(cacheKey('/units', { page: 1 }))
    expect(cacheKey('/staff', { active: false })).not.toBe(cacheKey('/staff', {}))
  })

  it('sin parámetros es solo el recurso', () => {
    expect(cacheKey('/staff')).toBe('/staff')
  })
})

describe('isCacheFresh', () => {
  it('vigente mientras no vence el TTL', () => {
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(100_000)
    const stamp = stampCache()
    vi.setSystemTime(129_999)
    expect(isCacheFresh(stamp, 30_000)).toBe(true)
    vi.setSystemTime(130_000)
    expect(isCacheFresh(stamp, 30_000)).toBe(false)
  })

  it('una mutación posterior al pedido lo vuelve viejo (aun en el mismo ms); lo pedido después sigue vigente', () => {
    const before = stampCache()
    invalidateCaches()
    expect(isCacheFresh(before, 30_000)).toBe(false)
    expect(isCacheFresh(stampCache(), 30_000)).toBe(true)
  })
})

describe('cachedRequest', () => {
  it('sirve de la caché dentro del TTL y recarga al vencer', async () => {
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(200_000)
    const loader = vi.fn(async () => 'a')
    expect(await cachedRequest('/t-ttl', 1000, loader)).toBe('a')
    expect(await cachedRequest('/t-ttl', 1000, loader)).toBe('a')
    expect(loader).toHaveBeenCalledTimes(1)
    vi.setSystemTime(201_001)
    await cachedRequest('/t-ttl', 1000, loader)
    expect(loader).toHaveBeenCalledTimes(2)
  })

  it('llamadas simultáneas a la misma clave comparten una sola carga', async () => {
    let resolve!: (v: string) => void
    const loader = vi.fn(() => new Promise<string>((r) => { resolve = r }))
    const p1 = cachedRequest('/t-shared', 1000, loader)
    const p2 = cachedRequest('/t-shared', 1000, loader)
    resolve('x')
    expect(await p1).toBe('x')
    expect(await p2).toBe('x')
    expect(loader).toHaveBeenCalledTimes(1)
  })

  it('un error no se guarda: el siguiente intento vuelve a cargar', async () => {
    const failing = Promise.reject(new Error('mal'))
    failing.catch(() => {})
    await expect(cachedRequest('/t-err', 1000, () => failing)).rejects.toThrow('mal')
    expect(await cachedRequest('/t-err', 1000, async () => 'ok')).toBe('ok')
  })

  it('tras invalidateCaches() vuelve a cargar', async () => {
    const loader = vi.fn(async () => 'a')
    await cachedRequest('/t-inv', 60_000, loader)
    invalidateCaches()
    await cachedRequest('/t-inv', 60_000, loader)
    expect(loader).toHaveBeenCalledTimes(2)
  })
})
