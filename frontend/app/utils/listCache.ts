import type { PaginatedListCache } from '#andromeda/composables/usePaginatedList'
import type { CacheStamp } from '#leo-client/lib/requestCache'

/**
 * Caché de páginas para `usePaginatedList({ cache: listCache('/staff') })`:
 * vigente 30 s (`LIST_CACHE_TTL`) y mientras no haya habido una mutación de
 * `useLeoAppApi` (`invalidateCaches` cambia la época que lleva el sello).
 */
export function listCache(scope: string): PaginatedListCache<CacheStamp> {
  return { scope, stamp: stampCache, isFresh: stamp => isCacheFresh(stamp, LIST_CACHE_TTL) }
}
