import { mountSuspended } from '@nuxt/test-utils/runtime'
import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { button, flushAll } from '~/testing/dom'
import type { VersionRecord } from '~/utils/versioning'
import UiVersionSection, { type UiVersionSectionApi } from './UiVersionSection.vue'

enableAutoUnmount(afterEach)

type FileVersion = VersionRecord & { has_file: boolean }

function record(id: string, n: number, status: VersionRecord['status'], hasFile: boolean): FileVersion {
  return { id, version_number: n, status, published_at: null, change_notes: null, has_file: hasFile }
}

async function mountSection(versions: FileVersion[], extra: Partial<UiVersionSectionApi> = {}) {
  const api: UiVersionSectionApi = {
    list: async () => versions,
    create: async () => ({ id: 'new' }),
    publish: vi.fn(async () => ({})),
    retire: async () => ({}),
    editorPath: id => `/x/${id}`,
    ...extra
  }
  const wrapper = await mountSuspended(UiVersionSection, { props: { api } })
  await flushAll()
  return { root: wrapper.element as HTMLElement, api }
}

describe('UiVersionSection', () => {
  it('sin badges ni bloqueo se comporta como antes', async () => {
    const { root } = await mountSection([record('a', 1, 'draft', false)])
    expect(root.textContent).toContain('Borrador')
    expect((button(root, 'Publicar') as HTMLButtonElement).disabled).toBe(false)
  })

  it('muestra los chips del módulo junto al estado', async () => {
    const { root } = await mountSection(
      [record('a', 1, 'published', true), record('b', 2, 'draft', false)],
      { badges: v => [(v as FileVersion).has_file ? { label: 'PDF adjunto', variant: 'success' } : { label: 'Sin archivo', variant: 'neutral' }] }
    )
    expect(root.textContent).toContain('PDF adjunto')
    expect(root.textContent).toContain('Sin archivo')
  })

  it('deshabilita Publicar de un borrador bloqueado y explica el motivo', async () => {
    const { root } = await mountSection(
      [record('a', 1, 'draft', false)],
      { publishBlockedReason: v => (v as FileVersion).has_file ? null : 'Adjunta el PDF antes de publicar.' }
    )
    const publish = button(root, 'Publicar') as HTMLButtonElement
    expect(publish.disabled).toBe(true)
    expect(publish.title).toBe('Adjunta el PDF antes de publicar.')
    expect(root.textContent).toContain('Adjunta el PDF antes de publicar.')
  })

  it('habilita Publicar cuando el módulo no lo bloquea', async () => {
    const { root } = await mountSection(
      [record('a', 1, 'draft', true)],
      { publishBlockedReason: v => (v as FileVersion).has_file ? null : 'Adjunta el PDF antes de publicar.' }
    )
    expect((button(root, 'Publicar') as HTMLButtonElement).disabled).toBe(false)
  })
})
