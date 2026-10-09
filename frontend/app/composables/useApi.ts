import type { ApiError } from '~/types/api'

/** Opciones aceptadas por `$fetch`, sin el `method` (lo fija cada verbo). */
type FetchOptions = Omit<NonNullable<Parameters<typeof $fetch>[1]>, 'method' | 'body'>

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
      return new ApiRequestError(data as ApiError, fetchErr.status)
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
        message: fetchErr.statusText ?? 'Ocurrió un error al comunicarse con el servidor.'
      },
      fetchErr.status
    )
  }

  return new ApiRequestError({
    code: 'network_error',
    message: 'No se pudo establecer conexión con el servidor.'
  })
}

/**
 * Cliente HTTP del núcleo. Todas las llamadas a la API pasan por aquí,
 * envueltas en los composables de cada módulo (useStaff, etc.).
 */
export function useApi() {
  const config = useRuntimeConfig()

  async function request<T>(
    path: string,
    method: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE',
    body?: unknown,
    options: RequestOptions = {}
  ): Promise<T> {
    const { cacheTtl, ...fetchOptions } = options
    const send = async () => {
      try {
        return await $fetch<T>(path, {
          baseURL: resolveApiBase(config, import.meta.server),
          method,
          body: body as BodyInit | Record<string, unknown> | null | undefined,
          ...fetchOptions
        })
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
