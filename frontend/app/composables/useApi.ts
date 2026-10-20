import type { LeoRequestOptions } from '#leo-client/lib/transport'
import type { ApiError } from '~/types/api'

/** Query string de una llamada (`params` es alias de `query`). */
type QueryParams = object

/** Opciones de una llamada (el `method` y el `body` los fija cada verbo). */
interface FetchOptions {
  query?: QueryParams
  params?: QueryParams
  signal?: AbortSignal
}

/**
 * Opciones de una llamada: las de `$fetch` más `cacheTtl` (ms), solo para GET:
 * guarda la respuesta en la caché del navegador (`cachedRequest`) por ese
 * tiempo. Toda mutación (POST/PATCH/PUT/DELETE) exitosa invalida TODO lo
 * cacheado (catálogos y listados).
 */
type RequestOptions = FetchOptions & { cacheTtl?: number }

/**
 * Error tipado que envuelve el AppError uniforme devuelto por el backend
 * (o un mensaje genérico si la respuesta no trae ese formato, p. ej. un 500
 * sin cuerpo o un error de red).
 */
export class ApiRequestError extends Error {
  code: string
  details?: unknown
  status?: number

  constructor(error: ApiError, status?: number) {
    super(error.message)
    this.name = 'ApiRequestError'
    this.code = error.code
    this.details = error.details
    this.status = status
  }
}

function toApiError(err: unknown): ApiRequestError {
  if (err && typeof err === 'object' && 'data' in err) {
    const fetchErr = err as { data?: unknown, status?: number, statusText?: string }
    const data = fetchErr.data
    if (data && typeof data === 'object' && 'code' in data && 'message' in data) {
      const apiError = data as ApiError
      // 403 de un tag de acción (`leo_sdk`: details.action): se nombra el permiso.
      if (fetchErr.status === 403 && apiError.code === 'forbidden') {
        const action = (apiError.details as { action?: string } | null | undefined)?.action
        return new ApiRequestError({ ...apiError, message: forbiddenMessage(action, apiError.message) }, fetchErr.status)
      }
      return new ApiRequestError(apiError, fetchErr.status)
    }
    // 422 de validación de schema de FastAPI (RequestValidationError):
    // `{ detail: [{ loc, msg, type }] }`. Se normaliza a ApiRequestError con
    // `details` = la lista, que `mapApiErrorToForm` traduce a errores por campo.
    if (data && typeof data === 'object' && 'detail' in data) {
      const detail = (data as { detail: unknown }).detail
      if (Array.isArray(detail)) {
        return new ApiRequestError(
          {
            code: 'request_validation',
            message: 'Algunos datos no son válidos. Revisa los campos marcados.',
            details: detail
          },
          fetchErr.status
        )
      }
      if (typeof detail === 'string') {
        return new ApiRequestError({ code: 'http_error', message: detail }, fetchErr.status)
      }
    }
    return new ApiRequestError(
      {
        code: 'unknown_error',
        message: toUserMessage(err)
      },
      fetchErr.status
    )
  }

  return new ApiRequestError({
    code: 'network_error',
    message: toUserMessage(err)
  })
}

/**
 * Cliente HTTP del núcleo. Todas las llamadas a la API pasan por aquí,
 * envueltas en los composables de cada módulo (useStaff, etc.). Van por el
 * solicitante firmado de leo-client (`useLeoApi`: cookie + DPoP); un 401 de
 * sesión lleva al login (lo hace leo-client) y un 403 trae el permiso faltante.
 */
export function useApi() {
  const config = useRuntimeConfig()
  const leoApi = useLeoApi()

  async function request<T>(
    path: string,
    method: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE',
    body?: unknown,
    options: RequestOptions = {}
  ): Promise<T> {
    const { cacheTtl, ...fetchOptions } = options
    const send = async () => {
      try {
        const { query, params, signal } = fetchOptions
        return await leoApi<T>(
          toLeoPath(resolveApiBase(config, false), config.public.leo.apiBase, path),
          { method, body, query: (query ?? params) as LeoRequestOptions['query'], signal }
        )
      } catch (err) {
        throw toApiError(err)
      }
    }

    if (method === 'GET') {
      if (!cacheTtl) return send()
      const params = (fetchOptions.query ?? fetchOptions.params ?? {}) as Record<string, unknown>
      return cachedRequest(cacheKey(path, params), cacheTtl, send)
    }
    const result = await send()
    // Tras cualquier mutación no se muestran datos viejos: se invalida todo
    // (listados y catálogos), sin adivinar qué recursos la muestran.
    if (import.meta.client) invalidateCaches()
    return result
  }

  return {
    get: <T>(path: string, options: RequestOptions = {}) =>
      request<T>(path, 'GET', undefined, options),
    post: <T>(path: string, body?: unknown, options: RequestOptions = {}) =>
      request<T>(path, 'POST', body, options),
    patch: <T>(path: string, body?: unknown, options: RequestOptions = {}) =>
      request<T>(path, 'PATCH', body, options),
    put: <T>(path: string, body?: unknown, options: RequestOptions = {}) =>
      request<T>(path, 'PUT', body, options),
    delete: <T>(path: string, options: RequestOptions = {}) =>
      request<T>(path, 'DELETE', undefined, options)
  }
}
