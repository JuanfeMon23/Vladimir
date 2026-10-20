import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiRequestError } from '~/composables/useApi'
import { fakePage } from '~/testing/fakeApi'
import { signInWith } from '~/testing/session'
import { button, click, control, flushAll, setValue } from '~/testing/dom'
import type { ConsentDocumentVersionRead } from '../../../../types/consent-documents'
import VersionEditorPage from './[versionId].vue'

const fake = await vi.hoisted(async () => (await import('~/testing/fakeApi')).createFakeApi())
mockNuxtImport('useApi', () => () => fake.api)

enableAutoUnmount(afterEach)

function version(overrides: Partial<ConsentDocumentVersionRead> = {}): ConsentDocumentVersionRead {
  return {
    id: 'v1',
    consent_document_id: 'd1',
    version_number: 2,
    status: 'draft',
    published_at: null,
    change_notes: null,
    content: '# Texto original',
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

const WITH_FILE = { has_file: true, file_content_type: 'application/pdf', file_sha256: 'a'.repeat(64), file_size_bytes: 2048 }

beforeEach(() => {
  // La navegación pasa por el middleware de leo-client: requiere sesión.
  signInWith([])
  fake.reset()
  document.body.innerHTML = ''
  fake.routes['GET /consent-documents/d1'] = { id: 'd1', code: 'CONSENT_VIH', name: 'Consentimiento VIH', document_type: 'consentimiento_informado', is_active: true }
})

function useVersion(v: ConsentDocumentVersionRead) {
  fake.routes['GET /consent-documents/d1/versions'] = fakePage([v])
}

async function mountPage() {
  const wrapper = await mountSuspended(VersionEditorPage, { route: '/consent-documents/d1/versions/v1', attachTo: document.body })
  await flushAll()
  return wrapper.element.parentElement as HTMLElement
}

function publishButton(root: HTMLElement) {
  return button(root, 'Publicar') as HTMLButtonElement
}

describe('editor de versión de documento a firmar', () => {
  it('sin archivo: muestra "Sin archivo" y Publicar deshabilitado con la explicación', async () => {
    useVersion(version())
    const root = await mountPage()
    expect(root.textContent).toContain('Sin archivo')
    expect(publishButton(root).disabled).toBe(true)
    expect(root.textContent).toContain('Adjunta el PDF antes de publicar.')
  })

  it('con archivo: "PDF adjunto" y Publicar habilitado', async () => {
    useVersion(version(WITH_FILE))
    const root = await mountPage()
    expect(root.textContent).toContain('PDF adjunto')
    expect(publishButton(root).disabled).toBe(false)
  })

  it('adjuntar un PDF habilita Publicar sin descartar lo escrito en el borrador', async () => {
    useVersion(version())
    fake.routes['PATCH /consent-documents/d1/versions/v1'] = version(WITH_FILE)
    const root = await mountPage()
    await setValue(control<HTMLTextAreaElement>(root, 'Contenido'), '# Cambio sin guardar')
    const input = root.querySelector<HTMLInputElement>('input[type="file"]')!
    Object.defineProperty(input, 'files', { value: [new File(['%PDF-1.4 x'], 'a.pdf', { type: 'application/pdf' })], configurable: true })
    input.dispatchEvent(new Event('change', { bubbles: true }))
    await flushAll()
    expect(root.textContent).toContain('PDF adjunto')
    expect(publishButton(root).disabled).toBe(false)
    expect(control<HTMLTextAreaElement>(root, 'Contenido').value).toBe('# Cambio sin guardar')
  })

  it('publicada: solo Ver/Descargar, sin controles de archivo ni Publicar', async () => {
    useVersion(version({ ...WITH_FILE, status: 'published', published_at: '2026-10-09T00:00:00Z' }))
    const root = await mountPage()
    const labels = [...root.querySelectorAll('button')].map(el => el.textContent?.trim())
    expect(labels).toContain('Ver')
    expect(labels).toContain('Descargar')
    for (const text of ['Publicar', 'Reemplazar', 'Quitar', 'Adjuntar PDF']) expect(labels).not.toContain(text)
  })

  it('si llega el 422 missing_fields file_base64 al publicar, lo describe en español', async () => {
    useVersion(version(WITH_FILE))
    fake.failures['POST /consent-documents/d1/versions/v1/publish'] = new ApiRequestError(
      { code: 'validation_error', message: 'Faltan campos obligatorios para publicar la version: file_base64.', details: { missing_fields: ['file_base64'] } },
      422
    )
    const root = await mountPage()
    await click(publishButton(root))
    const alert = [...root.querySelectorAll('[role="alert"]')].find(el => el.textContent?.includes('Faltan campos'))!
    expect(alert.textContent).toContain('Adjunta el PDF antes de publicar.')
  })
})
