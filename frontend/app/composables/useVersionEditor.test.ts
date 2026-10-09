import { describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountSuspended } from '@nuxt/test-utils/runtime'
import { defineComponent } from 'vue'
import { versionInUseCodes, type VersionRecord } from '~/utils/versioning'
import { ApiRequestError } from './useApi'
import { useVersionEditor, type UseVersionEditorOptions } from './useVersionEditor'

function version(status: VersionRecord['status'], n = 1): VersionRecord {
  return { id: `v${n}`, version_number: n, status, published_at: null, change_notes: null }
}

function rejected(err: unknown): Promise<never> {
  const p = Promise.reject(err)
  p.catch(() => {})
  return p
}

async function host(overrides: Partial<UseVersionEditorOptions<VersionRecord>> = {}) {
  const options: UseVersionEditorOptions<VersionRecord> = {
    load: async () => version('draft'),
    publish: async () => version('published'),
    retire: async () => version('retired'),
    ...overrides
  }
  let editor!: ReturnType<typeof useVersionEditor<VersionRecord>>
  await mountSuspended(defineComponent({
    setup() {
      editor = useVersionEditor(options)
      return () => null
    }
  }))
  await flushPromises()
  return editor
}

describe('useVersionEditor', () => {
  it('carga la versión al montar y llama onChange', async () => {
    const onChange = vi.fn()
    const editor = await host({ onChange })
    expect(editor.loading).toBe(false)
    expect(editor.version?.status).toBe('draft')
    expect(editor.isDraft).toBe(true)
    expect(editor.isPublished).toBe(false)
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ id: 'v1' }))
  })

  it('loading es true hasta que termina la carga', async () => {
    let resolve!: (v: VersionRecord) => void
    const editor = await host({ load: () => new Promise((r) => { resolve = r }) })
    expect(editor.loading).toBe(true)
    resolve(version('draft'))
    await flushPromises()
    expect(editor.loading).toBe(false)
  })

  it('si la versión no existe, loadError dice que no se encontró', async () => {
    const onChange = vi.fn()
    const editor = await host({ load: async () => null, onChange })
    expect(editor.loadError).toBe('No se encontró la versión solicitada.')
    expect(editor.version).toBeNull()
    expect(editor.loading).toBe(false)
    expect(onChange).not.toHaveBeenCalled()
  })

  it('si la carga falla, loadError trae el mensaje (o uno genérico)', async () => {
    const a = await host({ load: () => rejected(new Error('Sin conexión.')) })
    expect(a.loadError).toBe('Sin conexión.')
    expect(a.loading).toBe(false)
    const b = await host({ load: () => rejected('x') })
    expect(b.loadError).toBe('No se pudo cargar la versión.')
  })

  it('publish() actualiza la versión a publicada, notifica y marca publishing', async () => {
    let resolve!: (v: VersionRecord) => void
    const onChange = vi.fn()
    const editor = await host({ publish: () => new Promise((r) => { resolve = r }), onChange })
    const pending = editor.publish()
    expect(editor.publishing).toBe(true)
    resolve(version('published'))
    await pending
    expect(editor.publishing).toBe(false)
    expect(editor.isPublished).toBe(true)
    expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ status: 'published' }))
  })

  it('publish() fallido deja actionError y details (campos faltantes) sin cambiar la versión', async () => {
    const failure = new ApiRequestError(
      { code: 'publish_incomplete', message: 'Faltan datos.', details: { missing: ['sections'] } },
      409
    )
    const editor = await host({ publish: () => rejected(failure) })
    await editor.publish()
    expect(editor.actionError).toBe('Faltan datos.')
    expect(editor.actionErrorDetails).toEqual({ missing: ['sections'] })
    expect(editor.isDraft).toBe(true)
    expect(editor.publishing).toBe(false)
  })

  it('publish() con un error sin mensaje usa el genérico y details null', async () => {
    const editor = await host({ publish: () => rejected('x') })
    await editor.publish()
    expect(editor.actionError).toBe('No se pudo publicar la versión.')
    expect(editor.actionErrorDetails).toBeNull()
  })

  it('un publish exitoso limpia el error de la acción anterior', async () => {
    let fail = true
    const editor = await host({
      publish: () => (fail
        ? rejected(new ApiRequestError({ code: 'x', message: 'mal', details: { a: 1 } }))
        : Promise.resolve(version('published')))
    })
    await editor.publish()
    expect(editor.actionError).toBe('mal')
    fail = false
    await editor.publish()
    expect(editor.actionError).toBeNull()
    expect(editor.actionErrorDetails).toBeNull()
  })

  it('retirar: ask + confirm retira, cierra el modal y actualiza la versión', async () => {
    const editor = await host({ load: async () => version('published') })
    editor.retirement.ask(editor.version)
    expect(editor.retirement.open).toBe(true)
    await editor.retirement.confirm()
    expect(editor.retirement.open).toBe(false)
    expect(editor.version?.status).toBe('retired')
  })

  it('retirar con 409 version_in_use deja el modal abierto con el mensaje y los códigos en errorCause', async () => {
    const failure = new ApiRequestError(
      { code: 'version_in_use', message: 'La versión está en uso.', details: { lab_test_codes: ['GLU', 'HEM'] } },
      409
    )
    const editor = await host({ load: async () => version('published'), retire: () => rejected(failure) })
    editor.retirement.ask(editor.version)
    await editor.retirement.confirm()
    expect(editor.retirement.open).toBe(true)
    expect(editor.retirement.error).toBe('La versión está en uso.')
    expect(editor.retirement.errorCause).toBe(failure)
    expect(versionInUseCodes(editor.retirement.errorCause)).toEqual(['GLU', 'HEM'])
    expect(editor.isPublished).toBe(true)
  })

  it('patchVersion() actualiza la versión sin llamar onChange (el formulario no se reinicia)', async () => {
    const onChange = vi.fn()
    const editor = await host({ onChange })
    onChange.mockClear()
    editor.patchVersion({ ...version('draft'), change_notes: 'nuevo' })
    expect(editor.version?.change_notes).toBe('nuevo')
    expect(onChange).not.toHaveBeenCalled()
  })

  it('reload() vuelve a cargar y limpia loadError', async () => {
    let fail = true
    const editor = await host({
      load: () => (fail ? rejected(new Error('mal')) : Promise.resolve(version('draft', 2)))
    })
    expect(editor.loadError).toBe('mal')
    fail = false
    await editor.reload()
    expect(editor.loadError).toBeNull()
    expect(editor.version?.id).toBe('v2')
  })
})
