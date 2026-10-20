import { describe, expect, it } from 'vitest'

describe('configuración de leo-client en Vladimir', () => {
  it('usa el transporte bff contra el backend de la app, con /auth y el callback propio', () => {
    const leo = useRuntimeConfig().public.leo
    expect(leo.transport).toBe('bff')
    expect(leo.authPath).toBe('/auth')
    expect(leo.callbackPath).toBe('/leo/callback')
    expect(leo.appSlug).toBe('vladimir')
    expect(leo.appName).toBe('Vladimir')
  })

  it('la API de Vladimir cuelga de la base de Leo (una sola URL de backend)', () => {
    const { apiBase, leo } = useRuntimeConfig().public
    expect(apiBase.startsWith(leo.apiBase)).toBe(true)
  })

  it('la página de retorno de login está registrada en /leo/callback', () => {
    expect(useRouter().resolve('/leo/callback').matched.length).toBeGreaterThan(0)
  })
})
