import { describe, expect, it } from 'vitest'
import { ApiRequestError } from '~/composables/useApi'
import { versionInUseCodes } from './versioning'

describe('versionInUseCodes', () => {
  it('409 version_in_use: devuelve los códigos de examen que usan la versión', () => {
    const err = new ApiRequestError(
      {
        code: 'version_in_use',
        message: 'No se puede retirar la versión: la usan los exámenes (GLU, HEM).',
        details: { id: 'v1', lab_test_codes: ['GLU', 'HEM'] }
      },
      409
    )
    expect(versionInUseCodes(err)).toEqual(['GLU', 'HEM'])
  })

  it('otro error, sin códigos o con details mal formados: lista vacía', () => {
    expect(versionInUseCodes(new ApiRequestError({ code: 'conflict', message: 'x', details: { lab_test_codes: ['A'] } }, 409))).toEqual([])
    expect(versionInUseCodes(new ApiRequestError({ code: 'version_in_use', message: 'x', details: { id: 'v1' } }, 409))).toEqual([])
    expect(versionInUseCodes(new ApiRequestError({ code: 'version_in_use', message: 'x', details: { lab_test_codes: 'GLU' } }, 409))).toEqual([])
    expect(versionInUseCodes(new Error('x'))).toEqual([])
    expect(versionInUseCodes(null)).toEqual([])
  })
})
