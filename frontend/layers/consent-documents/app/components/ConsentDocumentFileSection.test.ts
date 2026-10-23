import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { apiError } from '~/testing/apiError'
import { button, click, flushAll } from '#andromeda/testing/dom'
import type { ConsentDocumentVersionRead } from '../types/consent-documents'
import ConsentDocumentFileSection from './ConsentDocumentFileSection.vue'

const fake = await vi.hoisted(async () => (await import('~/testing/fakeApi')).createFakeApi())
mockNuxtImport('useLeoAppApi', () => () => fake.api)

enableAutoUnmount(afterEach)

const SHA = 'abcdef0123456789'.repeat(4)

function version(overrides: Partial<ConsentDocumentVersionRead> = {}): ConsentDocumentVersionRead {
  return {
    id: 'v1',
    consent_document_id: 'd1',
    version_number: 2,
    status: 'draft',
    published_at: null,
    change_notes: null,
    content: '# Texto',
    signer: 'paciente',
    has_file: false,
    file_content_type: null,
    file_sha256: null,
    file_size_bytes: null,
    created_at: '2026-10-09T00:00:00Z',
    updated_at: '2026-10-09T00:00:00Z',
    ...overrides
  }
}

const WITH_FILE = {
  has_file: true,
  file_content_type: 'application/pdf',
  file_sha256: SHA,
  file_size_bytes: 1536
}

beforeEach(() => {
  fake.reset()
  document.body.innerHTML = ''
  Object.assign(URL, { createObjectURL: vi.fn(() => 'blob:x'), revokeObjectURL: vi.fn() })
})

async function mountSection(v: ConsentDocumentVersionRead, editable = true) {
  const wrapper = await mountSuspended(ConsentDocumentFileSection, {
    props: { version: v, documentCode: 'CONSENT_VIH', editable },
    attachTo: document.body
  })
  await flushAll()
  const root = wrapper.element.parentElement as HTMLElement
  return { wrapper, root }
}

function pdfFile(name = 'consentimiento.pdf', content = '%PDF-1.4 hola', type = 'application/pdf') {
  return new File([content], name, { type })
}

async function choose(root: HTMLElement, file: File) {
  const input = root.querySelector<HTMLInputElement>('input[type="file"]')!
  Object.defineProperty(input, 'files', { value: [file], configurable: true })
  input.dispatchEvent(new Event('change', { bubbles: true }))
  await flushAll()
}

function hasButton(root: ParentNode, text: string) {
  return [...root.querySelectorAll('button')].some(el => el.textContent?.trim() === text)
}

describe('ConsentDocumentFileSection', () => {
  it('sin archivo: "Sin archivo" y solo Adjuntar (editable)', async () => {
    const { root } = await mountSection(version())
    expect(root.textContent).toContain('Sin archivo')
    expect(hasButton(root, 'Adjuntar PDF')).toBe(true)
    for (const text of ['Ver', 'Descargar', 'Quitar', 'Reemplazar']) expect(hasButton(root, text)).toBe(false)
  })

  it('con archivo: tamaño legible, tipo y huella corta; copia la completa', async () => {
    const writeText = vi.fn(async () => {})
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    const { root } = await mountSection(version(WITH_FILE))
    expect(root.textContent).toContain('PDF adjunto')
    expect(root.textContent).toContain('application/pdf · 1,5 KB')
    expect(root.textContent).toContain('abcdef012345…')
    expect(root.textContent).not.toContain(SHA)
    await click(button(root, 'Copiar huella'))
    expect(writeText).toHaveBeenCalledWith(SHA)
    expect(root.textContent).toContain('Copiada')
  })

  it('publicada/retirada: solo Ver y Descargar, sin input de archivo', async () => {
    const { root } = await mountSection(version({ ...WITH_FILE, status: 'published' }), false)
    expect(hasButton(root, 'Ver')).toBe(true)
    expect(hasButton(root, 'Descargar')).toBe(true)
    for (const text of ['Reemplazar', 'Quitar', 'Adjuntar PDF']) expect(hasButton(root, text)).toBe(false)
    expect(root.querySelector('input[type="file"]')).toBeNull()
  })

  it('adjuntar envía base64 puro (sin data:) por PATCH y emite la versión actualizada', async () => {
    const updated = version(WITH_FILE)
    fake.routes['PATCH /consent-documents/d1/versions/v1'] = updated
    const { wrapper, root } = await mountSection(version())
    await choose(root, pdfFile())
    const [body] = fake.bodies('PATCH', '/consent-documents/d1/versions/v1') as [{ file_base64: string }]
    expect(Object.keys(body)).toEqual(['file_base64'])
    expect(body.file_base64.startsWith('data:')).toBe(false)
    expect(atob(body.file_base64)).toBe('%PDF-1.4 hola')
    expect(wrapper.emitted('changed')?.[0]).toEqual([updated])
  })

  it('reemplazar usa el mismo PATCH', async () => {
    fake.routes['PATCH /consent-documents/d1/versions/v1'] = version(WITH_FILE)
    const { root } = await mountSection(version(WITH_FILE))
    expect(hasButton(root, 'Reemplazar')).toBe(true)
    await choose(root, pdfFile('nuevo.pdf', '%PDF-1.7 otro'))
    const [body] = fake.bodies('PATCH', '/consent-documents/d1/versions/v1') as [{ file_base64: string }]
    expect(atob(body.file_base64)).toBe('%PDF-1.7 otro')
  })

  it.each([
    ['un archivo que no es PDF', pdfFile('foto.png', 'x', 'image/png'), 'El archivo no es un PDF válido.'],
    ['un archivo vacío', pdfFile('vacio.pdf', ''), 'El archivo está vacío.']
  ])('rechaza en cliente %s sin llamar a la API', async (_name, file, message) => {
    const { wrapper, root } = await mountSection(version())
    await choose(root, file)
    expect(root.querySelector('[role="alert"]')?.textContent).toContain(message)
    expect(fake.requests).not.toHaveBeenCalled()
    expect(wrapper.emitted('changed')).toBeUndefined()
  })

  it('no limita el tamaño en cliente: lo envía y el 422 too_large muestra el mensaje del backend', async () => {
    fake.failures['PATCH /consent-documents/d1/versions/v1'] = apiError(
      { code: 'validation_error', message: 'El archivo supera el tamaño máximo de 8 MB.', details: { field: 'file_base64', reason: 'too_large' } },
      422
    )
    const { root } = await mountSection(version())
    const big = pdfFile('grande.pdf')
    Object.defineProperty(big, 'size', { value: 50 * 1024 * 1024 })
    await choose(root, big)
    expect(fake.requests).toHaveBeenCalledOnce()
    expect(root.querySelector('[role="alert"]')?.textContent).toContain('El archivo supera el tamaño máximo de 8 MB.')
  })

  it('muestra en español el 422 del backend por reason', async () => {
    fake.failures['PATCH /consent-documents/d1/versions/v1'] = apiError(
      { code: 'validation_error', message: 'texto del backend', details: { field: 'file_base64', reason: 'not_pdf' } },
      422
    )
    const { wrapper, root } = await mountSection(version())
    await choose(root, pdfFile())
    expect(root.querySelector('[role="alert"]')?.textContent).toContain('El archivo no es un PDF válido.')
    expect(wrapper.emitted('changed')).toBeUndefined()
  })

  it('quitar pide confirmación y manda file_base64: null', async () => {
    const updated = version()
    fake.routes['PATCH /consent-documents/d1/versions/v1'] = updated
    const { wrapper, root } = await mountSection(version(WITH_FILE))
    await click(button(root, 'Quitar'))
    expect(fake.requests).not.toHaveBeenCalled()
    const dialog = document.body.querySelector<HTMLElement>('[role="dialog"]')!
    expect(dialog.textContent).toContain('Quitar archivo')
    await click(button(dialog, 'Quitar'))
    expect(fake.bodies('PATCH', '/consent-documents/d1/versions/v1')).toEqual([{ file_base64: null }])
    expect(wrapper.emitted('changed')?.[0]).toEqual([updated])
  })

  it('Ver pide el archivo solo al abrir y lo muestra con su nombre de descarga', async () => {
    fake.routes['GET /consent-document-versions/v1/file'] = {
      content_type: 'application/pdf', sha256: SHA, size_bytes: 13, base64: btoa('%PDF-1.4 hola')
    }
    const { root } = await mountSection(version(WITH_FILE))
    expect(fake.requests).not.toHaveBeenCalled()
    await click(button(root, 'Ver'))
    expect(fake.requests).toHaveBeenCalledWith('GET', '/consent-document-versions/v1/file', undefined)
    const dialog = document.body.querySelector<HTMLElement>('[role="dialog"]')!
    expect(dialog.textContent).toContain('CONSENT_VIH-v2.pdf')
    expect(dialog.querySelector('object')).not.toBeNull()
  })

  it('Descargar baja <codigo>-v<N>.pdf', async () => {
    fake.routes['GET /consent-document-versions/v1/file'] = {
      content_type: 'application/pdf', sha256: SHA, size_bytes: 13, base64: btoa('%PDF-1.4 hola')
    }
    const names: string[] = []
    const original = HTMLAnchorElement.prototype.click
    HTMLAnchorElement.prototype.click = function () { names.push(this.download) }
    try {
      const { root } = await mountSection(version(WITH_FILE))
      await click(button(root, 'Descargar'))
    } finally {
      HTMLAnchorElement.prototype.click = original
    }
    expect(names).toEqual(['CONSENT_VIH-v2.pdf'])
  })
})
