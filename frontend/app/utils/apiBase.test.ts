import { describe, expect, it } from 'vitest'
import { resolveApiBase } from './apiBase'

const config = { apiBaseServer: 'http://backend.test/api/v1', public: { apiBase: 'http://public.test/api/v1' } }

describe('resolveApiBase', () => {
  it('en el navegador usa siempre la base pública', () => {
    expect(resolveApiBase(config, false)).toBe('http://public.test/api/v1')
  })

  it('en el servidor usa la base privada si está configurada', () => {
    expect(resolveApiBase(config, true)).toBe('http://backend.test/api/v1')
  })

  it('en el servidor sin base privada cae a la pública', () => {
    expect(resolveApiBase({ ...config, apiBaseServer: '' }, true)).toBe('http://public.test/api/v1')
  })

  it('sin base pública configurada lanza un error claro', () => {
    const message = 'Falta configurar NUXT_PUBLIC_API_BASE (ver frontend/.env.example).'
    expect(() => resolveApiBase({ public: { apiBase: '' } }, false)).toThrow(message)
    expect(() => resolveApiBase({ apiBaseServer: '', public: { apiBase: '' } }, true)).toThrow(message)
  })

  it('en el servidor con base privada no exige la pública', () => {
    expect(resolveApiBase({ apiBaseServer: 'http://backend.test/api/v1', public: { apiBase: '' } }, true))
      .toBe('http://backend.test/api/v1')
  })
})
