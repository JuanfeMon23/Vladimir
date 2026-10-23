import { mountSuspended } from '@nuxt/test-utils/runtime'
import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { button, click, flushAll } from '#andromeda/testing/dom'
import UiPdfPreviewModal from '#andromeda/components/ui/UiPdfPreviewModal.vue'

enableAutoUnmount(afterEach)

const BASE64 = btoa('%PDF-1.4 contenido')

let createObjectURL: ReturnType<typeof vi.fn>
let revokeObjectURL: ReturnType<typeof vi.fn>

beforeEach(() => {
  document.body.innerHTML = ''
  let n = 0
  createObjectURL = vi.fn(() => `blob:test/${++n}`)
  revokeObjectURL = vi.fn()
  Object.assign(URL, { createObjectURL, revokeObjectURL })
})

function dialog() {
  return document.body.querySelector<HTMLElement>('[role="dialog"]')
}

async function mountModal(open: boolean, load: () => Promise<{ base64: string, content_type?: string }> = vi.fn(async () => ({ base64: BASE64, content_type: 'application/pdf' }))) {
  const wrapper = await mountSuspended(UiPdfPreviewModal, {
    props: { open, filename: 'CONSENT_VIH-v2.pdf', load },
    attachTo: document.body
  })
  await flushAll()
  return { wrapper, load }
}

describe('UiPdfPreviewModal', () => {
  it('no pide el archivo mientras está cerrado', async () => {
    const { load } = await mountModal(false)
    expect(load).not.toHaveBeenCalled()
    expect(createObjectURL).not.toHaveBeenCalled()
    expect(dialog()).toBeNull()
  })

  it('al abrir pide el archivo una vez y lo muestra embebido desde un Blob URL', async () => {
    const { wrapper, load } = await mountModal(false)
    await wrapper.setProps({ open: true })
    await flushAll()
    expect(load).toHaveBeenCalledTimes(1)
    expect(createObjectURL).toHaveBeenCalledTimes(1)
    const blob = createObjectURL.mock.calls[0]![0] as Blob
    expect(blob.type).toBe('application/pdf')
    expect(blob.size).toBe('%PDF-1.4 contenido'.length)
    const embed = dialog()!.querySelector('object')!
    expect(embed.getAttribute('data')).toBe('blob:test/1')
    expect(embed.getAttribute('type')).toBe('application/pdf')
    // Fallback para navegadores que no muestran PDF.
    expect(embed.textContent).toContain('Descargar')
  })

  it('arrancar abierto también carga el archivo', async () => {
    const { load } = await mountModal(true)
    expect(load).toHaveBeenCalledTimes(1)
    expect(dialog()!.querySelector('object')).not.toBeNull()
  })

  it('al cerrar revoca el Blob URL y al reabrir vuelve a pedir el archivo', async () => {
    const { wrapper, load } = await mountModal(true)
    await wrapper.setProps({ open: false })
    await flushAll()
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:test/1')
    await wrapper.setProps({ open: true })
    await flushAll()
    expect(load).toHaveBeenCalledTimes(2)
    expect(createObjectURL).toHaveBeenCalledTimes(2)
  })

  it('al desmontar revoca el Blob URL', async () => {
    const { wrapper } = await mountModal(true)
    wrapper.unmount()
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:test/1')
  })

  it('si se cierra antes de que llegue el archivo no crea ni deja un Blob URL', async () => {
    let resolve!: (v: { base64: string }) => void
    const load = vi.fn(() => new Promise<{ base64: string }>((r) => { resolve = r }))
    const { wrapper } = await mountModal(true, load)
    await wrapper.setProps({ open: false })
    resolve({ base64: BASE64 })
    await flushAll()
    expect(createObjectURL).not.toHaveBeenCalled()
  })

  it('muestra el error de carga y no crea Blob URL', async () => {
    const failure = new Error('No hay archivo.')
    // Función simple (no vi.fn): Vitest 5 reporta como error el rechazo que devuelve un mock.
    const load = (async () => { throw failure }) as never
    await mountModal(true, load)
    expect(dialog()!.textContent).toContain('No hay archivo.')
    expect(createObjectURL).not.toHaveBeenCalled()
  })

  it('Descargar baja el archivo con el nombre indicado', async () => {
    const clicked: string[] = []
    const original = HTMLAnchorElement.prototype.click
    HTMLAnchorElement.prototype.click = function () { clicked.push(this.download) }
    try {
      await mountModal(true)
      await click(button(dialog()!, 'Descargar'))
    } finally {
      HTMLAnchorElement.prototype.click = original
    }
    expect(clicked).toEqual(['CONSENT_VIH-v2.pdf'])
  })
})
