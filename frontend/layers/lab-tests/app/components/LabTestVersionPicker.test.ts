import { mountSuspended } from '@nuxt/test-utils/runtime'
import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { z } from 'zod'
import { ApiRequestError } from '~/composables/useApi'
import { control, flushAll, optionLabels, setValue } from '~/testing/dom'
import type { LabTestCatalogOption, LabTestVersionOption, LabTestVersionWithOwner } from '../types/lab-tests'
import LabTestVersionPicker from './LabTestVersionPicker.vue'

enableAutoUnmount(afterEach)

const OWNERS: LabTestCatalogOption[] = [
  { id: 'o1', code: 'A', name: 'Activa', is_active: true },
  { id: 'o2', code: 'B', name: 'Inactiva asignada', is_active: false },
  { id: 'o3', code: 'C', name: 'Inactiva libre', is_active: false },
  { id: 'o4', code: 'D', name: 'Sin publicadas', is_active: true }
]

const VERSIONS: Record<string, LabTestVersionOption[]> = {
  o1: [
    { id: 'v12', version_number: 2, status: 'published' },
    { id: 'v11', version_number: 1, status: 'retired' },
    { id: 'v13', version_number: 3, status: 'draft' }
  ],
  o2: [{ id: 'v21', version_number: 1, status: 'retired' }],
  o3: [{ id: 'v31', version_number: 1, status: 'published' }],
  o4: [{ id: 'v41', version_number: 1, status: 'draft' }]
}

// Llamadas registradas con spies; las respuestas (y el fallo) fuera de `vi.fn`
// (Vitest 5 reporta como error del test el rechazo que devuelve un mock).
const calls = { published: vi.fn<(ownerId: string) => void>(), version: vi.fn<(versionId: string) => void>() }
let versionFailure: Error | null = null

async function loadPublishedVersions(ownerId: string) {
  calls.published(ownerId)
  return (VERSIONS[ownerId] ?? []).filter(version => version.status === 'published')
}

async function loadVersion(versionId: string): Promise<LabTestVersionWithOwner> {
  calls.version(versionId)
  if (versionFailure) throw versionFailure
  const ownerId = Object.keys(VERSIONS).find(id => VERSIONS[id]!.some(version => version.id === versionId))!
  return { ...VERSIONS[ownerId]!.find(version => version.id === versionId)!, owner: OWNERS.find(owner => owner.id === ownerId)! }
}

beforeEach(() => {
  calls.published.mockReset()
  calls.version.mockReset()
  versionFailure = null
})

/** Monta el selector dentro de un formulario con `version_id` inicial; devuelve el estado del form. */
async function mountPicker(initial: string | null) {
  let form!: ReturnType<typeof useZodForm>
  const Host = defineComponent({
    setup() {
      form = useZodForm(z.object({ version_id: zOptionalId() }), { initialValues: { version_id: initial ?? '' } })
      return () => h(LabTestVersionPicker, {
        name: 'version_id',
        ownerLabel: 'Etiqueta',
        ownerPlaceholder: 'Sin etiqueta',
        emptyVersionsHint: 'Esta etiqueta no tiene versiones publicadas.',
        loadOwners: async () => OWNERS,
        loadPublishedVersions,
        loadVersion
      })
    }
  })
  const wrapper = await mountSuspended(Host, { attachTo: document.body })
  await flushAll()
  const root = wrapper.element as HTMLElement
  return {
    form,
    owner: () => control<HTMLSelectElement>(root, 'Etiqueta'),
    version: () => control<HTMLSelectElement>(root, 'Versión publicada'),
    text: () => root.textContent ?? ''
  }
}

describe('LabTestVersionPicker', () => {
  it('sin versión asignada: solo dueños activos y la versión deshabilitada hasta elegir uno', async () => {
    const picker = await mountPicker(null)
    expect(optionLabels(picker.owner())).toEqual(['Sin etiqueta', 'Activa (A)', 'Sin publicadas (D)'])
    expect(picker.version().disabled).toBe(true)
    expect(picker.text()).toContain('Elige primero: etiqueta.')
    expect(calls.published).not.toHaveBeenCalled()
    expect(calls.version).not.toHaveBeenCalled()
  })

  it('al elegir un dueño pide solo sus versiones publicadas', async () => {
    const picker = await mountPicker(null)
    await setValue(picker.owner(), 'o1')
    await flushAll()
    expect(calls.published).toHaveBeenCalledWith('o1')
    expect(picker.version().disabled).toBe(false)
    expect(optionLabels(picker.version())).toEqual(['Sin versión', 'Versión 2'])
    await setValue(picker.version(), 'v12')
    expect(picker.form.values.version_id).toBe('v12')
  })

  it('un dueño sin versiones publicadas muestra el aviso', async () => {
    const picker = await mountPicker(null)
    await setValue(picker.owner(), 'o4')
    await flushAll()
    expect(optionLabels(picker.version())).toEqual(['Sin versión'])
    expect(picker.text()).toContain('Esta etiqueta no tiene versiones publicadas.')
  })

  it('con una versión asignada consulta su dueño directo (sin recorrer las demás entidades) y la muestra aunque esté retirada', async () => {
    const picker = await mountPicker('v11')
    expect(calls.version).toHaveBeenCalledExactlyOnceWith('v11')
    expect(calls.published.mock.calls).toEqual([['o1']])
    expect(picker.owner().value).toBe('o1')
    expect(picker.version().value).toBe('v11')
    expect(optionLabels(picker.version())).toEqual(['Sin versión', 'Versión 1 (retirada)', 'Versión 2'])
  })

  it('el dueño inactivo de la versión asignada se sigue mostrando, marcado "(inactivo)"', async () => {
    const picker = await mountPicker('v21')
    expect(optionLabels(picker.owner())).toEqual([
      'Sin etiqueta',
      'Activa (A)',
      'Inactiva asignada (B) (inactivo)',
      'Sin publicadas (D)'
    ])
    expect(picker.owner().value).toBe('o2')
    expect(picker.version().value).toBe('v21')
    expect(optionLabels(picker.version())).toEqual(['Sin versión', 'Versión 1 (retirada)'])
  })

  it('cambiar de dueño limpia la versión elegida', async () => {
    const picker = await mountPicker('v12')
    expect(picker.form.values.version_id).toBe('v12')
    await setValue(picker.owner(), 'o4')
    await flushAll()
    expect(picker.form.values.version_id).toBeNull()
    expect(picker.version().value).toBe('')
  })

  it('si la versión asignada no se encuentra (404) muestra el error', async () => {
    versionFailure = new ApiRequestError({ code: 'not_found', message: 'No existe una versión con id \'v99\'.' }, 404)
    const picker = await mountPicker('v99')
    expect(picker.text()).toContain('No existe una versión con id \'v99\'.')
  })
})
