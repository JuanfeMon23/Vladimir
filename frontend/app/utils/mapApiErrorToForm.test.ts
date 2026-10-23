import { describe, expect, it } from 'vitest'
import { apiError } from '~/testing/apiError'
import { mapApiErrorToForm } from '#andromeda/utils/mapApiErrorToForm'

const fields = ['code', 'name', 'unit_id', 'analyte_id']

function appError(code: string, message: string, details?: unknown, status = 422) {
  return apiError({ code, message, details }, status)
}

describe('mapApiErrorToForm', () => {
  it('409 conflict con details.<campo> asigna el mensaje a ese campo', () => {
    const result = mapApiErrorToForm(appError('conflict', 'Ya existe.', { code: 'HEM' }, 409), { fields })
    expect(result).toEqual({ formError: null, fieldErrors: { code: 'Ya existe.' } })
  })

  it('409 conflict de analito duplicado en la versión va al campo analyte_id', () => {
    const result = mapApiErrorToForm(
      appError('conflict', 'El analito ya está incluido (activo) en esta versión.', { analyte_id: 'a1' }, 409),
      { fields }
    )
    expect(result.fieldErrors).toEqual({ analyte_id: 'El analito ya está incluido (activo) en esta versión.' })
    expect(result.formError).toBeNull()
  })

  it('422 inactive_reference / invalid_reference ubican el error por la clave de details', () => {
    const inactive = mapApiErrorToForm(appError('inactive_reference', 'La unidad «mg/dL» está inactiva.', { unit_id: 'u1' }), { fields })
    expect(inactive.fieldErrors).toEqual({ unit_id: 'La unidad «mg/dL» está inactiva.' })
    const invalid = mapApiErrorToForm(appError('invalid_reference', 'El analito con id \'x\' no existe.', { analyte_id: 'x' }), { fields })
    expect(invalid.fieldErrors).toEqual({ analyte_id: 'El analito con id \'x\' no existe.' })
  })

  it('una clave de details que no es campo del formulario deja el mensaje como error general', () => {
    const result = mapApiErrorToForm(
      appError('reference_range_overlap', 'El rango se solapa con otro rango activo.', { overlapping_id: 'r1' }),
      { fields }
    )
    expect(result).toEqual({ formError: 'El rango se solapa con otro rango activo.', fieldErrors: {} })
  })

  it('details.field (valor) nombra el campo afectado: 422 validation_error de sample_types', () => {
    const result = mapApiErrorToForm(
      appError('validation_error', 'El examen debe tener al menos un tipo de muestra.', { field: 'sample_types' }),
      { fields: [...fields, 'sample_types'] }
    )
    expect(result).toEqual({ formError: null, fieldErrors: { sample_types: 'El examen debe tener al menos un tipo de muestra.' } })
  })

  it('details.field que no es campo del formulario queda como error general', () => {
    const result = mapApiErrorToForm(appError('validation_error', 'Mal.', { field: 'otro' }), { fields })
    expect(result).toEqual({ formError: 'Mal.', fieldErrors: {} })
  })

  it('409 delete_forbidden es un error general', () => {
    const result = mapApiErrorToForm(appError('delete_forbidden', 'No se puede eliminar.', { table: 'units' }, 409), { fields })
    expect(result.formError).toBe('No se puede eliminar.')
  })

  it('fieldMap traduce claves del backend a rutas del formulario', () => {
    const result = mapApiErrorToForm(appError('conflict', 'Duplicado.', { area_id: 'x' }), {
      fields: ['area'],
      fieldMap: { area_id: 'area' }
    })
    expect(result.fieldErrors).toEqual({ area: 'Duplicado.' })
  })

  it('422 de schema (request_validation) usa el último segmento de loc', () => {
    const err = appError('request_validation', 'Algunos datos no son válidos.', [
      { loc: ['body', 'name'], msg: 'Campo requerido' },
      { loc: ['body', 'otro'], msg: 'Ignorado' },
      { loc: ['body', 'name'], msg: 'Segundo error del mismo campo' }
    ])
    expect(mapApiErrorToForm(err, { fields })).toEqual({ formError: null, fieldErrors: { name: 'Campo requerido' } })
  })

  it('request_validation sin campos conocidos va al error general', () => {
    const err = appError('request_validation', 'Algunos datos no son válidos.', [{ loc: ['body', 'x'], msg: 'm' }])
    expect(mapApiErrorToForm(err, { fields }).formError).toBe('Algunos datos no son válidos.')
  })

  it('un error que no es de la API da un mensaje genérico legible (no expone el texto crudo)', () => {
    const generic = 'Ocurrió un error inesperado. Inténtalo de nuevo.'
    expect(mapApiErrorToForm(new Error('Falló'), { fields }).formError).toBe(generic)
    expect(mapApiErrorToForm('raro', { fields }).formError).toBe(generic)
  })
})
