import type { CatalogCreate, CatalogItemBySlug, CatalogSlug, CatalogUpdate } from '~/types/catalogs'

/**
 * Llamadas a la API de los catálogos de categoría (`/catalogs/{slug}`), vía
 * `useLeoAppApi`. Sin DELETE: un valor se desactiva (`is_active`), no se borra.
 */
export function useCatalogApi() {
  const api = useLeoAppApi()

  /** Array simple ordenado por `sort_order`; `includeInactive` agrega los inactivos. */
  function list<S extends CatalogSlug>(
    slug: S,
    opts: { includeInactive?: boolean, cacheTtl?: number, signal?: AbortSignal } = {}
  ) {
    const { includeInactive, ...request } = opts
    return api.get<CatalogItemBySlug[S][]>(`/catalogs/${slug}`, {
      params: includeInactive ? { include_inactive: true } : {},
      ...request
    })
  }

  function create<S extends CatalogSlug>(slug: S, payload: CatalogCreate<S>) {
    return api.post<CatalogItemBySlug[S]>(`/catalogs/${slug}`, payload)
  }

  function update<S extends CatalogSlug>(slug: S, id: string, payload: CatalogUpdate<S>) {
    return api.patch<CatalogItemBySlug[S]>(`/catalogs/${slug}/${id}`, payload)
  }

  return { list, create, update }
}
