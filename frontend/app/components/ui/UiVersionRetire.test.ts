import { mountSuspended } from '@nuxt/test-utils/runtime'
import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { apiError } from '~/testing/apiError'
import { signInWith } from '#leo-client/testing/session'
import { button, click, flushAll } from '#andromeda/testing/dom'
import type { VersionRecord } from '~/utils/versioning'
import UiVersionEditor from './UiVersionEditor.vue'
import UiVersionSection from './UiVersionSection.vue'

// La pila de modales es de módulo: cada test desmonta los suyos.
enableAutoUnmount(afterEach)

// El versionado es fail-closed: cada acción exige su tag.
const PERMISSIONS = { create: 'v.create', edit: 'v.edit', publish: 'v.publish', retire: 'v.retire' }

const PUBLISHED: VersionRecord = { id: 'v1', version_number: 1, status: 'published', published_at: '2026-10-01T00:00:00Z', change_notes: null }

const IN_USE = apiError(
  {
    code: 'version_in_use',
    message: 'No se puede retirar la versión: la usan los exámenes activos (GLU, HEM).',
    details: { id: 'v1', lab_test_codes: ['GLU', 'HEM'] }
  },
  409
)

// El rechazo se arma fuera de `vi.fn` (Vitest 5).
const retired = vi.fn<(id: string) => void>()
let retireFailure: Error | null = null
async function retire(id: string) {
  retired(id)
  if (retireFailure) throw retireFailure
  return { ...PUBLISHED, status: 'retired' as const }
}

beforeEach(() => {
  retired.mockReset()
  retireFailure = null
  signInWith(Object.values(PERMISSIONS))
  document.body.innerHTML = ''
})

function dialog() {
  return document.body.querySelector<HTMLElement>('[role="dialog"]')
}

describe('retirar versión (UiVersionSection)', () => {
  async function mountSection() {
    await mountSuspended(UiVersionSection, {
      props: {
        permissions: PERMISSIONS,
        api: {
          list: async () => [PUBLISHED],
          create: async () => ({ id: 'v2' }),
          publish: async () => PUBLISHED,
          retire,
          editorPath: (id: string) => `/x/versions/${id}`
        }
      },
      attachTo: document.body
    })
    await flushAll()
  }

  it('409 version_in_use: el modal sigue abierto con el mensaje y los códigos de examen', async () => {
    retireFailure = IN_USE
    await mountSection()
    await click(button(document.body, 'Retirar'))
    await click(button(dialog()!, 'Retirar'))

    expect(retired).toHaveBeenCalledWith('v1')
    const modal = dialog()!
    const alert = modal.querySelector('[role="alert"]')!
    expect(alert.textContent).toContain('No se puede retirar la versión: la usan los exámenes activos (GLU, HEM).')
    expect(alert.textContent).toContain('Exámenes activos que la usan:')
    expect([...alert.querySelectorAll('li')].map(li => li.textContent?.trim())).toEqual(['GLU', 'HEM'])
  })

  it('otro error: solo el mensaje, sin lista', async () => {
    retireFailure = apiError({ code: 'network_error', message: 'No se pudo establecer conexión con el servidor.' })
    await mountSection()
    await click(button(document.body, 'Retirar'))
    await click(button(dialog()!, 'Retirar'))
    const alert = dialog()!.querySelector('[role="alert"]')!
    expect(alert.textContent).toContain('No se pudo establecer conexión con el servidor.')
    expect(alert.querySelector('li')).toBeNull()
  })
})

describe('retirar versión (UiVersionEditor + useVersionEditor)', () => {
  it('409 version_in_use: muestra el mensaje y los códigos; la versión sigue publicada', async () => {
    retireFailure = IN_USE
    const Host = defineComponent({
      setup() {
        const editor = useVersionEditor({ load: async () => PUBLISHED, publish: async () => PUBLISHED, retire: () => retire('v1') })
        return () => h(UiVersionEditor, { editor, backTo: '/x', permissions: PERMISSIONS })
      }
    })
    const wrapper = await mountSuspended(Host, { attachTo: document.body })
    await flushAll()
    await click(button(wrapper.element as HTMLElement, 'Retirar'))
    await click(button(dialog()!, 'Retirar'))

    const items = [...dialog()!.querySelectorAll('[role="alert"] li')].map(li => li.textContent?.trim())
    expect(items).toEqual(['GLU', 'HEM'])
    expect(wrapper.text()).toContain('Publicada')
  })

  it('si retira bien, cierra el modal y la versión queda retirada', async () => {
    const Host = defineComponent({
      setup() {
        const editor = useVersionEditor({ load: async () => PUBLISHED, publish: async () => PUBLISHED, retire: () => retire('v1') })
        return () => h(UiVersionEditor, { editor, backTo: '/x', permissions: PERMISSIONS })
      }
    })
    const wrapper = await mountSuspended(Host, { attachTo: document.body })
    await flushAll()
    await click(button(wrapper.element as HTMLElement, 'Retirar'))
    await click(button(dialog()!, 'Retirar'))
    expect(dialog()).toBeNull()
    expect(wrapper.text()).toContain('Retirada')
  })
})
