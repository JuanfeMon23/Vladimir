/**
 * Vigencia de las lecturas de la API en el navegador. Los listados
 * (`usePaginatedList`, `useAsyncData` + `getCachedData`) y los catálogos
 * (`useApi().get(..., { cacheTtl })`) comparten una regla: un dato guardado
 * sirve mientras no venza su TTL y no haya habido una mutación después de
 * pedirlo. Toda mutación exitosa de `useApi` llama a `invalidateCaches()`.
 */

/** TTL de un listado paginado (30 s). */
export const LIST_CACHE_TTL = 30_000
/** TTL de un catálogo para selects/modales (5 min). */
export const CATALOG_CACHE_TTL = 300_000

/** Sello de una lectura: hora y época de INICIO de la petición. */
export interface CacheStamp { at: number, epoch: number }

let epoch = 0

/** Sello para una petición que se va a hacer ahora. */
export function stampCache(): CacheStamp {
  return { at: Date.now(), epoch }
}

/** Marca como viejo todo lo pedido hasta ahora (se llama tras una mutación). */
export function invalidateCaches() {
  epoch++
}

/** ¿Sigue vigente una lectura sellada? No si venció el TTL o hubo una mutación después. */
export function isCacheFresh(stamp: CacheStamp, ttl: number): boolean {
  return stamp.epoch === epoch && Date.now() - stamp.at < ttl
}

/**
 * Clave estable de un recurso + parámetros: ignora `undefined`/`null`/`''` y
 * el orden de las claves, p. ej. `/staff?{"page":1}`.
 */
export function cacheKey(resource: string, params: Record<string, unknown> = {}): string {
  const entries = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null && v !== '')
    .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
  if (!entries.length) return resource
  return `${resource}?${JSON.stringify(Object.fromEntries(entries))}`
}

const catalogs = new Map<string, { stamp: CacheStamp, promise: Promise<unknown> }>()

/**
 * Catálogo/lectura cacheada fuera de `useAsyncData` (p. ej. al abrir un
 * modal): una sola carga para llamadas simultáneas, vigente según
 * `isCacheFresh`. Los errores no se guardan. En el servidor siempre carga
 * (la caché se compartiría entre usuarios).
 */
export function cachedRequest<T>(key: string, ttl: number, loader: () => Promise<T>): Promise<T> {
  if (import.meta.server) return loader()
  const hit = catalogs.get(key)
  if (hit && isCacheFresh(hit.stamp, ttl)) return hit.promise as Promise<T>
  const entry = { stamp: stampCache(), promise: loader() }
  catalogs.set(key, entry)
  entry.promise.catch(() => {
    if (catalogs.get(key) === entry) catalogs.delete(key)
  })
  return entry.promise as Promise<T>
}
