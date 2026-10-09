import { describe, expect, it } from 'vitest'
import { ApiRequestError } from './useApi'
import { useConfirmAction } from './useConfirmAction'

describe('useConfirmAction', () => {
  it('confirm() ejecuta la acción con el objetivo y cierra el modal', async () => {
    const done: string[] = []
    const action = useConfirmAction(async (id: string) => { done.push(id) })
    action.ask('v1')
    expect(action.open).toBe(true)
    await action.confirm()
    expect(done).toEqual(['v1'])
    expect(action.open).toBe(false)
    expect(action.error).toBeNull()
    expect(action.errorCause).toBeNull()
  })

  it('si falla deja el modal abierto con el mensaje y el error original (errorCause)', async () => {
    const failure = new ApiRequestError(
      { code: 'version_in_use', message: 'No se puede retirar la versión.', details: { lab_test_codes: ['GLU'] } },
      409
    )
    const action = useConfirmAction(async () => { throw failure })
    action.ask('v1')
    await action.confirm()
    expect(action.open).toBe(true)
    expect(action.error).toBe('No se puede retirar la versión.')
    expect(action.errorCause).toBe(failure)

    // Volver a pedir la confirmación limpia el error.
    action.ask('v2')
    expect(action.error).toBeNull()
    expect(action.errorCause).toBeNull()
  })
})
