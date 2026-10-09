import { describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { useChildCollection } from './useChildCollection'

interface Child { id: string }

function rejected(err: unknown): Promise<never> {
  const p = Promise.reject(err)
  p.catch(() => {})
  return p
}

function setup(opts: { refetch?: () => Promise<Child[]>, errorMessage?: string } = {}) {
  const open = ref(true)
  const parent = ref<Child[]>([{ id: 'a' }])
  const children = useChildCollection<Child>({
    open,
    initial: () => parent.value,
    refetch: opts.refetch ?? (async () => [{ id: 'a' }, { id: 'b' }]),
    errorMessage: opts.errorMessage
  })
  return { open, parent, children }
}

describe('useChildCollection', () => {
  it('con el modal abierto al montar arranca con los hijos iniciales de la entidad', () => {
    const { children } = setup()
    expect(children.items).toEqual([{ id: 'a' }])
    expect(children.loading).toBe(false)
    expect(children.error).toBeNull()
  })

  it('al abrir el modal padre se reinicia con initial() y limpia el error', async () => {
    const { open, parent, children } = setup({ refetch: () => rejected(new Error('mal')) })
    await children.refresh()
    expect(children.error).toBe('mal')
    parent.value = [{ id: 'z' }]
    open.value = false
    await flushPromises()
    open.value = true
    await flushPromises()
    expect(children.items).toEqual([{ id: 'z' }])
    expect(children.error).toBeNull()
  })

  it('cerrar el modal padre no reinicia la lista', async () => {
    const { open, parent, children } = setup()
    parent.value = [{ id: 'z' }]
    open.value = false
    await flushPromises()
    expect(children.items).toEqual([{ id: 'a' }])
  })

  it('refresh() recarga los hijos y marca loading mientras corre', async () => {
    let resolve!: (v: Child[]) => void
    const refetch = vi.fn(() => new Promise<Child[]>((r) => { resolve = r }))
    const { children } = setup({ refetch })
    const pending = children.refresh()
    expect(children.loading).toBe(true)
    resolve([{ id: 'n' }])
    await pending
    expect(children.loading).toBe(false)
    expect(children.items).toEqual([{ id: 'n' }])
  })

  it('si refresh() falla deja el mensaje del error y conserva los hijos', async () => {
    const { children } = setup({ refetch: () => rejected(new Error('No hay conexión.')) })
    await children.refresh()
    expect(children.error).toBe('No hay conexión.')
    expect(children.loading).toBe(false)
    expect(children.items).toEqual([{ id: 'a' }])
  })

  it('un error sin mensaje usa errorMessage o el genérico', async () => {
    const a = setup({ refetch: () => rejected('x'), errorMessage: 'No se pudieron cargar los ítems.' })
    await a.children.refresh()
    expect(a.children.error).toBe('No se pudieron cargar los ítems.')
    const b = setup({ refetch: () => rejected('x') })
    await b.children.refresh()
    expect(b.children.error).toBe('No se pudo recargar la lista.')
  })

  it('un refresh exitoso limpia el error previo', async () => {
    let fail = true
    const { children } = setup({
      refetch: () => (fail ? rejected(new Error('mal')) : Promise.resolve([{ id: 'ok' }]))
    })
    await children.refresh()
    expect(children.error).toBe('mal')
    fail = false
    await children.refresh()
    expect(children.error).toBeNull()
    expect(children.items).toEqual([{ id: 'ok' }])
  })

  it('expone el modal anidado del hijo (crear / editar)', () => {
    const { children } = setup()
    children.modal.openCreate()
    expect(children.modal.open).toBe(true)
    expect(children.modal.entity).toBeNull()
    children.modal.openEdit({ id: 'a' })
    expect(children.modal.entity).toEqual({ id: 'a' })
  })
})
