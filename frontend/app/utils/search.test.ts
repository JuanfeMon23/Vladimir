import { describe, expect, it } from 'vitest'
import { SEARCH_MAX_LENGTH, SEARCH_MAX_WORDS, normalizeSearchTerm } from './search'

describe('normalizeSearchTerm', () => {
  it('recorta espacios al inicio y al final', () => {
    expect(normalizeSearchTerm('  herrera ')).toBe('herrera')
  })

  it('colapsa los espacios internos (no cuentan como palabras vacías)', () => {
    expect(normalizeSearchTerm('mg   dl\t x')).toBe('mg dl x')
  })

  it('vacío, solo espacios o valores no texto dan cadena vacía', () => {
    expect(normalizeSearchTerm('')).toBe('')
    expect(normalizeSearchTerm('   ')).toBe('')
    expect(normalizeSearchTerm(undefined)).toBe('')
    expect(normalizeSearchTerm(null)).toBe('')
    expect(normalizeSearchTerm(42)).toBe('')
  })

  it('limita a 100 caracteres (el backend responde 422 si excede)', () => {
    const out = normalizeSearchTerm('a'.repeat(250))
    expect(out).toHaveLength(SEARCH_MAX_LENGTH)
    expect(SEARCH_MAX_LENGTH).toBe(100)
  })

  it('limita a 8 palabras (el backend responde 422 si excede)', () => {
    const out = normalizeSearchTerm('uno dos tres cuatro cinco seis siete ocho nueve diez')
    expect(out).toBe('uno dos tres cuatro cinco seis siete ocho')
    expect(SEARCH_MAX_WORDS).toBe(8)
  })

  it('conserva tildes, mayúsculas y % _ literales (el backend los normaliza)', () => {
    expect(normalizeSearchTerm('Ñandú 50%_')).toBe('Ñandú 50%_')
  })

  it('no deja un espacio final al cortar a 100 caracteres', () => {
    const text = `${'a'.repeat(99)} bbb`
    expect(normalizeSearchTerm(text)).toBe('a'.repeat(99))
  })
})
