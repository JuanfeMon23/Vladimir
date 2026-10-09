import { mountSuspended } from '@nuxt/test-utils/runtime'
import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import { nextTick } from 'vue'
import UiModal from './UiModal.vue'

function dialog() {
  return document.body.querySelector<HTMLElement>('[role="dialog"]')
}

function pressEscape() {
  document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
}

// La pila de modales abiertos es de módulo: cada test desmonta los suyos.
enableAutoUnmount(afterEach)

describe('UiModal', () => {
  afterEach(() => {
    document.body.innerHTML = ''
    document.body.style.overflow = ''
  })

  it('abierto: renderiza un dialog accesible con título y descripción en body', async () => {
    await mountSuspended(UiModal, {
      props: { open: true, title: 'Editar área', description: 'Datos del área' },
      slots: { default: () => 'Contenido' },
      attachTo: document.body
    })
    const el = dialog()
    expect(el).not.toBeNull()
    expect(el!.getAttribute('aria-modal')).toBe('true')
    const title = document.getElementById(el!.getAttribute('aria-labelledby')!)
    expect(title?.textContent).toContain('Editar área')
    const description = document.getElementById(el!.getAttribute('aria-describedby')!)
    expect(description?.textContent).toContain('Datos del área')
    expect(el!.textContent).toContain('Contenido')
    expect(document.body.style.overflow).toBe('hidden')
  })

  it('cerrado: no renderiza nada', async () => {
    await mountSuspended(UiModal, { props: { open: false, title: 'X' }, attachTo: document.body })
    expect(dialog()).toBeNull()
  })

  it('Esc y el botón Cerrar emiten update:open=false y close', async () => {
    const wrapper = await mountSuspended(UiModal, { props: { open: true, title: 'X' }, attachTo: document.body })
    pressEscape()
    expect(wrapper.emitted('update:open')?.[0]).toEqual([false])
    expect(wrapper.emitted('close')).toHaveLength(1)

    document.body.querySelector<HTMLButtonElement>('button[aria-label="Cerrar"]')!.click()
    expect(wrapper.emitted('update:open')).toHaveLength(2)
  })

  it('no dismissable: ignora Esc y oculta el botón Cerrar', async () => {
    const wrapper = await mountSuspended(UiModal, {
      props: { open: true, title: 'X', dismissable: false },
      attachTo: document.body
    })
    pressEscape()
    expect(wrapper.emitted('update:open')).toBeUndefined()
    expect(document.body.querySelector('button[aria-label="Cerrar"]')).toBeNull()
  })

  it('el slot del pie recibe close(), que cierra aunque no sea dismissable', async () => {
    const wrapper = await mountSuspended(UiModal, {
      props: { open: true, title: 'X', dismissable: false },
      slots: { footer: ({ close }: { close: () => void }) => h('button', { id: 'cancel', onClick: close }, 'Cancelar') },
      attachTo: document.body
    })
    document.getElementById('cancel')!.click()
    expect(wrapper.emitted('update:open')?.[0]).toEqual([false])
  })

  it('al cerrar libera el bloqueo de scroll', async () => {
    const wrapper = await mountSuspended(UiModal, { props: { open: true, title: 'X' }, attachTo: document.body })
    await wrapper.setProps({ open: false })
    await nextTick()
    expect(document.body.style.overflow).toBe('')
  })
})
