import { describe, expect, it } from 'vitest'
import { describeFormulaProblem, formulaProblemMessages } from './formulaProblems'

describe('describeFormulaProblem', () => {
  it('syntax: usa el mensaje del backend', () => {
    expect(describeFormulaProblem({ reason: 'syntax', message: 'Sintaxis inválida: paréntesis sin cerrar.', codes: [] }))
      .toBe('Sintaxis inválida: paréntesis sin cerrar.')
  })

  it('unknown_code: lista los códigos que no son analitos de la versión', () => {
    expect(describeFormulaProblem({ reason: 'unknown_code', message: 'x', codes: ['AAA', 'BBB'] }))
      .toBe('Códigos que no son analitos de esta versión: AAA, BBB.')
  })

  it('inactive_code: lista los analitos inactivos', () => {
    expect(describeFormulaProblem({ reason: 'inactive_code', message: 'x', codes: ['CHOL'] }))
      .toBe('Analitos inactivos en la fórmula: CHOL.')
  })

  it('cycle: muestra el recorrido circular', () => {
    expect(describeFormulaProblem({ reason: 'cycle', message: 'x', codes: ['A', 'B', 'A'] }))
      .toBe('Referencia circular: A → B → A.')
  })

  it('motivo desconocido o sin códigos: cae al mensaje del backend', () => {
    expect(describeFormulaProblem({ reason: 'otro', message: 'Mensaje del backend.', codes: ['A'] })).toBe('Mensaje del backend.')
    expect(describeFormulaProblem({ reason: 'cycle', message: 'Circular.', codes: [] })).toBe('Circular.')
  })
})

describe('formulaProblemMessages', () => {
  it('lee details.problems de un 422 sobre el campo formula', () => {
    expect(formulaProblemMessages({
      field: 'formula',
      problems: [
        { reason: 'unknown_code', message: 'x', codes: ['ZZ'] },
        { reason: 'inactive_code', message: 'y', codes: ['HDL'] }
      ]
    })).toEqual([
      'Códigos que no son analitos de esta versión: ZZ.',
      'Analitos inactivos en la fórmula: HDL.'
    ])
  })

  it('devuelve [] si details no es de la fórmula', () => {
    expect(formulaProblemMessages(null)).toEqual([])
    expect(formulaProblemMessages({ field: 'code' })).toEqual([])
    expect(formulaProblemMessages({ field: 'formula', problems: 'x' })).toEqual([])
  })
})
