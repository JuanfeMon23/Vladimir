import { describe, expect, it } from 'vitest'
import {
  toJsonText,
  toSelectOptions,
  zJsonObject,
  zOptionalEmail,
  zOptionalEnum,
  zOptionalId,
  zOptionalNumber,
  zOptionalText,
  zRequiredEnum,
  zRequiredId,
  zRequiredNumber,
  zRequiredText
} from './zodFields'

function errorOf(result: { success: boolean, error?: { issues: { message: string }[] } }) {
  return result.success ? null : result.error?.issues[0]?.message
}

describe('zRequiredText', () => {
  const field = zRequiredText('El código es obligatorio.', 5)

  it('recorta y acepta texto dentro del límite', () => {
    expect(field.parse('  ABC ')).toBe('ABC')
  })

  it('rechaza vacío o solo espacios con el mensaje dado', () => {
    expect(errorOf(field.safeParse('   '))).toBe('El código es obligatorio.')
    expect(errorOf(field.safeParse(undefined))).toBe('El código es obligatorio.')
  })

  it('acepta el límite exacto y rechaza uno más', () => {
    expect(field.parse('12345')).toBe('12345')
    expect(errorOf(field.safeParse('123456'))).toBe('Máximo 5 caracteres.')
  })

  it('sin máximo no limita la longitud', () => {
    expect(zRequiredText('x').parse('a'.repeat(5000))).toHaveLength(5000)
  })
})

describe('zOptionalText', () => {
  it('convierte vacío, espacios, null y undefined en null', () => {
    const field = zOptionalText(10)
    expect(field.parse('')).toBeNull()
    expect(field.parse('   ')).toBeNull()
    expect(field.parse(null)).toBeNull()
    expect(field.parse(undefined)).toBeNull()
  })

  it('recorta y valida el máximo', () => {
    const field = zOptionalText(3)
    expect(field.parse(' ab ')).toBe('ab')
    expect(errorOf(field.safeParse('abcd'))).toBe('Máximo 3 caracteres.')
  })
})

describe('zOptionalEmail', () => {
  it('vacío → null y correo válido pasa', () => {
    expect(zOptionalEmail().parse('')).toBeNull()
    expect(zOptionalEmail().parse('a@b.co')).toBe('a@b.co')
  })

  it('rechaza un correo inválido', () => {
    expect(errorOf(zOptionalEmail().safeParse('no-es-correo'))).toBe('Ingresa un correo electrónico válido.')
  })
})

describe('zOptionalNumber / zRequiredNumber', () => {
  it('convierte texto de un input numérico en número y vacío en null', () => {
    const field = zOptionalNumber()
    expect(field.parse('12.5')).toBe(12.5)
    expect(field.parse(3)).toBe(3)
    expect(field.parse('')).toBeNull()
    expect(field.parse(null)).toBeNull()
  })

  it('valida número, mínimo y entero', () => {
    const field = zOptionalNumber({ min: 0, integer: true })
    expect(errorOf(field.safeParse('abc'))).toBe('Debe ser un número.')
    expect(errorOf(field.safeParse('-1'))).toBe('Debe ser mayor o igual a 0.')
    expect(errorOf(field.safeParse('1.5'))).toBe('Debe ser un número entero.')
    expect(field.parse('0')).toBe(0)
  })

  it('zRequiredNumber exige un valor', () => {
    const field = zRequiredNumber('El orden es obligatorio.', { min: 0 })
    expect(errorOf(field.safeParse(''))).toBe('El orden es obligatorio.')
    expect(field.parse('4')).toBe(4)
  })
})

describe('enums', () => {
  const VALUES = ['a', 'b'] as const

  it('zRequiredEnum acepta valores de la lista y rechaza vacío u otros', () => {
    const field = zRequiredEnum(VALUES, 'Selecciona uno.')
    expect(field.parse('a')).toBe('a')
    expect(errorOf(field.safeParse(''))).toBe('Selecciona uno.')
    expect(errorOf(field.safeParse('z'))).toBe('Selecciona uno.')
  })

  it('zOptionalEnum: vacío → null; fuera de la lista es error', () => {
    const field = zOptionalEnum(VALUES)
    expect(field.parse('')).toBeNull()
    expect(field.parse('b')).toBe('b')
    expect(errorOf(field.safeParse('z'))).toBe('Selecciona una opción válida.')
  })
})

describe('ids de selects', () => {
  it('zRequiredId rechaza vacío', () => {
    expect(errorOf(zRequiredId('Selecciona un área.').safeParse(''))).toBe('Selecciona un área.')
    expect(zRequiredId('x').parse('id-1')).toBe('id-1')
  })

  it('zOptionalId: vacío → null', () => {
    expect(zOptionalId().parse('')).toBeNull()
    expect(zOptionalId().parse('id-1')).toBe('id-1')
  })
})

describe('zJsonObject / toJsonText', () => {
  const field = zJsonObject('La configuración')

  it('vacío → objeto vacío y JSON de objeto → objeto', () => {
    expect(field.parse('')).toEqual({})
    expect(field.parse('{ "a": 1 }')).toEqual({ a: 1 })
  })

  it('rechaza JSON inválido o que no es objeto', () => {
    expect(errorOf(field.safeParse('{'))).toBe('La configuración debe ser un JSON válido.')
    expect(errorOf(field.safeParse('[1]'))).toBe('La configuración debe ser un objeto JSON ({ … }).')
  })

  it('toJsonText formatea con sangría y trata null como {}', () => {
    expect(toJsonText({ a: 1 })).toBe('{\n  "a": 1\n}')
    expect(toJsonText(null)).toBe('{}')
  })
})

describe('toSelectOptions', () => {
  it('convierte un mapa valor → etiqueta en opciones', () => {
    expect(toSelectOptions({ a: 'A', b: 'B' })).toEqual([
      { value: 'a', label: 'A' },
      { value: 'b', label: 'B' }
    ])
  })
})
