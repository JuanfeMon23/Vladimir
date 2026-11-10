import { describe, expect, it } from 'vitest'
import { CATALOG_FIXTURES } from '~/testing/catalogs'
import type { CatalogItem } from '~/types/catalogs'
import { catalogNameOf, catalogSelectOptions } from './catalogs'

const SIGNERS = CATALOG_FIXTURES['consent-signers']

function inactive(code: string, name: string): CatalogItem {
  return { ...SIGNERS[0]!, id: `${code}-id`, code, name, is_active: false }
}

describe('catalogNameOf', () => {
  it('devuelve el nombre del valor y, si no se conoce, el código tal cual', () => {
    expect(catalogNameOf(SIGNERS, 'paciente_o_representante')).toBe('Paciente o representante')
    expect(catalogNameOf(SIGNERS, 'nuevo_firmante')).toBe('nuevo_firmante')
  })

  it('sin valor devuelve vacío', () => {
    expect(catalogNameOf(SIGNERS, null)).toBe('')
    expect(catalogNameOf(SIGNERS, undefined)).toBe('')
    expect(catalogNameOf(SIGNERS, '')).toBe('')
  })

  it('resuelve también los valores inactivos', () => {
    expect(catalogNameOf([inactive('viejo', 'Firmante viejo')], 'viejo')).toBe('Firmante viejo')
  })
})

describe('catalogSelectOptions', () => {
  it('ofrece los activos con el código como valor y el nombre como etiqueta', () => {
    expect(catalogSelectOptions(SIGNERS)).toEqual([
      { value: 'paciente', label: 'Paciente' },
      { value: 'paciente_o_representante', label: 'Paciente o representante' }
    ])
  })

  it('omite los inactivos salvo que sean el valor actual, marcado "(inactivo)"', () => {
    const items = [...SIGNERS, inactive('viejo', 'Firmante viejo')]
    expect(catalogSelectOptions(items).map(option => option.value)).toEqual(['paciente', 'paciente_o_representante'])
    expect(catalogSelectOptions(items, 'viejo')).toContainEqual({ value: 'viejo', label: 'Firmante viejo (inactivo)' })
  })

  it('conserva un valor actual que el catálogo no trae (sin cargar o sin permiso) con su código', () => {
    expect(catalogSelectOptions([], 'paciente')).toEqual([{ value: 'paciente', label: 'paciente' }])
    expect(catalogSelectOptions(SIGNERS, 'otro_firmante').at(-1)).toEqual({ value: 'otro_firmante', label: 'otro_firmante' })
  })

  it('acepta varios valores actuales y no duplica los activos', () => {
    const options = catalogSelectOptions([...SIGNERS, inactive('viejo', 'Firmante viejo')], ['paciente', 'viejo', null])
    expect(options.map(option => option.value)).toEqual(['paciente', 'paciente_o_representante', 'viejo'])
  })
})
