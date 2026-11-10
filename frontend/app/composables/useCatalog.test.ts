import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { signInWith } from '#leo-client/testing/session'
import { flushAll } from '#andromeda/testing/dom'
import { apiError } from '~/testing/apiError'
import { CATALOG_FIXTURES, fakeCatalogs } from '~/testing/catalogs'
import { MODULE_VIEW } from '../utils/moduleAccess'

const fake = await vi.hoisted(async () => (await import('~/testing/fakeApi')).createFakeApi())
mockNuxtImport('useLeoAppApi', () => () => fake.api)

enableAutoUnmount(afterEach)

beforeEach(() => {
  fake.reset()
  fakeCatalogs(fake)
})

/** Monta un componente que usa el catálogo y devuelve la instancia reactiva. */
async function useCatalogInComponent<S extends 'sexes' | 'result-types' | 'duration-units'>(slug: S) {
  let catalog!: ReturnType<typeof useCatalog<S>>
  await mountSuspended(defineComponent({
    setup() {
      catalog = useCatalog(slug)
      return () => h('div')
    }
  }))
  await flushAll()
  return catalog
}

describe('useCatalog', () => {
  it('pide el catálogo con los inactivos y la caché de catálogo', async () => {
    signInWith([MODULE_VIEW.catalogs.tag])
    const catalog = await useCatalogInComponent('sexes')
    expect(fake.requests).toHaveBeenCalledWith('GET', '/catalogs/sexes', expect.objectContaining({ params: { include_inactive: true }, cacheTtl: CATALOG_CACHE_TTL }))
    expect(catalog.items).toEqual(CATALOG_FIXTURES.sexes)
    expect(catalog.error).toBeNull()
  })

  it('nameOf nombra el valor guardado y cae al código si no existe', async () => {
    signInWith([MODULE_VIEW.catalogs.tag])
    const catalog = await useCatalogInComponent('duration-units')
    expect(catalog.nameOf('horas')).toBe('Horas')
    expect(catalog.nameOf('semanas')).toBe('semanas')
  })

  it('optionsFor ofrece solo activos más el valor actual inactivo', async () => {
    signInWith([MODULE_VIEW.catalogs.tag])
    fake.routes['GET /catalogs/duration-units'] = [
      ...CATALOG_FIXTURES['duration-units'],
      { ...CATALOG_FIXTURES['duration-units'][0]!, id: 'seg', code: 'segundos', name: 'Segundos', is_active: false }
    ]
    const catalog = await useCatalogInComponent('duration-units')
    expect(catalog.optionsFor().map(option => option.value)).toEqual(['minutos', 'horas', 'dias'])
    expect(catalog.optionsFor('segundos')).toContainEqual({ value: 'segundos', label: 'Segundos (inactivo)' })
  })

  it('itemOf expone las banderas de comportamiento de la fila', async () => {
    signInWith([MODULE_VIEW.catalogs.tag])
    const catalog = await useCatalogInComponent('result-types')
    expect(catalog.itemOf('calculated')?.uses_formula).toBe(true)
    expect(catalog.itemOf('text')?.uses_unit).toBe(false)
    expect(catalog.itemOf('inexistente')).toBeUndefined()
    expect(catalog.firstActiveCode()).toBe('numeric')
  })

  it('sin el permiso catalogs.view no pide nada y avisa', async () => {
    signInWith([])
    const catalog = await useCatalogInComponent('sexes')
    expect(fake.requests).not.toHaveBeenCalled()
    expect(catalog.error).toBe('No tienes permiso para consultar catálogos.')
    expect(catalog.nameOf('male')).toBe('male')
  })

  it('un fallo de carga queda en error y deja la lista vacía', async () => {
    signInWith([MODULE_VIEW.catalogs.tag])
    fake.failures['GET /catalogs/sexes'] = apiError({ code: 'internal_error', message: 'Error del servidor.' }, 500)
    const catalog = await useCatalogInComponent('sexes')
    expect(catalog.error).toContain('error en el servidor')
    expect(catalog.items).toEqual([])
  })
})
