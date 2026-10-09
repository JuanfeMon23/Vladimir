/** Lo que `resolveApiBase` lee de `useRuntimeConfig()`. */
export interface ApiBaseConfig {
  apiBaseServer?: string
  public: { apiBase: string }
}

/**
 * URL base de la API: en el servidor (SSR) usa `apiBaseServer`
 * (`NUXT_API_BASE_SERVER`, p. ej. una red interna) si está configurada; en el
 * navegador, siempre la pública (`NUXT_PUBLIC_API_BASE`). Si el resultado está
 * vacío (no hay valor en `frontend/.env`) lanza un error claro.
 */
export function resolveApiBase(config: ApiBaseConfig, isServer: boolean): string {
  const base = isServer && config.apiBaseServer ? config.apiBaseServer : config.public.apiBase
  if (!base) throw new Error('Falta configurar NUXT_PUBLIC_API_BASE (ver frontend/.env.example).')
  return base
}
