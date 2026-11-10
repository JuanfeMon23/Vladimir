import type { CatalogItemBySlug, CatalogSlug } from '~/types/catalogs'

/**
 * Un catálogo de categoría para los selectores y etiquetas de un módulo:
 * carga `GET /catalogs/{slug}?include_inactive=true` (con caché de catálogo de
 * `useLeoAppApi`, que toda mutación invalida) y ofrece
 * - `nameOf(code)`: nombre legible de un valor guardado (activo o no);
 * - `optionsFor(current?)`: opciones de un `<UiSelect>` con solo activos más
 *   el valor actual aunque esté inactivo ("(inactivo)");
 * - `itemOf(code)`: la fila completa (p. ej. las banderas de un tipo de resultado).
 *
 * Devuelve un objeto reactivo (no se desestructura). Sin el permiso `vladimir.catalogs.view` no se pide nada (fail-closed): `error`
 * trae el aviso y los nombres caen al `code`. Las etiquetas salen de la API;
 * ningún módulo duplica la lista.
 */
export function useCatalog<S extends CatalogSlug>(slug: S) {
  type Item = CatalogItemBySlug[S]
  const catalogApi = useCatalogApi()
  const canView = useCan(MODULE_VIEW.catalogs.tag)

  const items = ref([]) as Ref<Item[]>
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function load() {
    if (!canView.value) {
      error.value = noViewMessage(MODULE_VIEW.catalogs)
      return
    }
    loading.value = true
    error.value = null
    try {
      items.value = await catalogApi.list(slug, { includeInactive: true, cacheTtl: CATALOG_CACHE_TTL })
    } catch (err) {
      error.value = leoErrorMessage(err)
    } finally {
      loading.value = false
    }
  }

  function itemOf(code: string | null | undefined): Item | undefined {
    return code ? items.value.find(item => item.code === code) : undefined
  }

  function nameOf(code: string | null | undefined) {
    return catalogNameOf(items.value, code)
  }

  function optionsFor(current?: string | null | readonly (string | null | undefined)[]) {
    return catalogSelectOptions(items.value, current)
  }

  /** Primer valor activo (en el orden de la API), para precargar un obligatorio. */
  function firstActiveCode(): string | undefined {
    return items.value.find(item => item.is_active)?.code
  }

  void load()

  // `reactive`: en las plantillas se lee `catalog.error` / `catalog.items` sin `.value`.
  return reactive({ items, loading, error, load, itemOf, nameOf, optionsFor, firstActiveCode })
}
