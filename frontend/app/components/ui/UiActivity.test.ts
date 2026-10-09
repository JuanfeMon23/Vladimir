import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'
import { z } from 'zod'
import UiActiveField from './UiActiveField.vue'
import UiActivityTimeline from './UiActivityTimeline.vue'
import UiFormModal from './UiFormModal.vue'
import UiToggleActiveModal from './UiToggleActiveModal.vue'

const { getMock } = vi.hoisted(() => ({ getMock: vi.fn() }))
mockNuxtImport('useApi', () => () => ({ get: getMock }))

enableAutoUnmount(afterEach)

const flush = async () => {
  for (let i = 0; i < 5; i++) await nextTick()
  await new Promise(resolve => setTimeout(resolve, 0))
}

beforeEach(() => {
  getMock.mockReset()
  getMock.mockResolvedValue({
    items: [
      { id: 'e2', entity_type: 'units', entity_id: 'u1', action: 'activated', reason: null, occurred_at: '2026-10-02T12:00:00Z' },
      { id: 'e1', entity_type: 'units', entity_id: 'u1', action: 'deactivated', reason: 'Duplicada', occurred_at: '2026-10-01T12:00:00Z' }
    ],
    total: 2,
    page: 1,
    page_size: 20
  })
  document.body.innerHTML = ''
})

describe('UiActivityTimeline', () => {
  it('muestra cada evento con su acción y su motivo (o "Sin motivo.")', async () => {
    const wrapper = await mountSuspended(UiActivityTimeline, { props: { entityType: 'units', entityId: 'u1' } })
    await flush()
    const items = wrapper.findAll('li')
    expect(items).toHaveLength(2)
    expect(items[0]!.text()).toContain('Activado')
    expect(items[0]!.text()).toContain('Sin motivo.')
    expect(items[1]!.text()).toContain('Desactivado')
    expect(items[1]!.text()).toContain('Duplicada')
    expect(items[1]!.find('time').attributes('datetime')).toBe('2026-10-01T12:00:00Z')
  })

  it('con events pinta la lista fija sin consultar la API', async () => {
    const wrapper = await mountSuspended(UiActivityTimeline, {
      props: {
        entityType: 'lab_areas',
        events: [{ id: 'x', entity_type: 'lab_areas', entity_id: '1', action: 'deactivated', reason: 'Cierre', occurred_at: '2026-10-02T12:00:00Z' }]
      }
    })
    await flush()
    expect(getMock).not.toHaveBeenCalled()
    expect(wrapper.findAll('li')).toHaveLength(1)
    expect(wrapper.text()).toContain('Cierre')
  })

  it('sin eventos muestra el mensaje vacío', async () => {
    getMock.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 })
    const wrapper = await mountSuspended(UiActivityTimeline, { props: { entityType: 'units', entityId: 'u1' } })
    await flush()
    expect(wrapper.text()).toContain('Sin cambios de estado registrados.')
  })
})

describe('UiActiveField', () => {
  function host(initial: boolean | undefined, startActive: boolean) {
    return defineComponent({
      setup() {
        useZodForm(z.object({ is_active: z.boolean(), activity_reason: zActivityReason() }), {
          initialValues: { is_active: startActive, activity_reason: '' }
        })
        return () => h(UiActiveField, { label: 'Activa', initial })
      }
    })
  }

  it('al crear no pide motivo', async () => {
    const wrapper = await mountSuspended(host(undefined, true))
    await wrapper.find('input[type="checkbox"]').setValue(false)
    await flush()
    expect(wrapper.text()).not.toContain('Motivo')
  })

  it('al editar pide el motivo solo cuando el estado cambia', async () => {
    const wrapper = await mountSuspended(host(true, true))
    expect(wrapper.text()).not.toContain('Motivo')
    await wrapper.find('input[type="checkbox"]').setValue(false)
    await flush()
    expect(wrapper.text()).toContain('Motivo de la desactivación')
    await wrapper.find('input[type="checkbox"]').setValue(true)
    await flush()
    expect(wrapper.text()).not.toContain('Motivo')
  })
})

describe('UiToggleActiveModal', () => {
  it('desactivar: botón danger "Desactivar" y el motivo escrito llega a la acción', async () => {
    const action = vi.fn(async () => {})
    let toggle!: ReturnType<typeof useToggleActive<{ id: string, is_active: boolean }>>
    const Host = defineComponent({
      setup() {
        toggle = useToggleActive(action)
        return () => h(UiToggleActiveModal, { state: toggle, noun: 'la sección', name: 'Serie roja' })
      }
    })
    await mountSuspended(Host, { attachTo: document.body })
    toggle.ask({ id: 's1', is_active: true })
    await flush()

    const dialog = document.body.querySelector('[role="dialog"]')!
    expect(dialog.textContent).toContain('Desactivar la sección')
    expect(dialog.textContent).toContain('«Serie roja»')
    const textarea = dialog.querySelector('textarea')!
    textarea.value = 'Se fusionó'
    textarea.dispatchEvent(new Event('input'))
    await flush()
    const confirm = [...dialog.querySelectorAll('button')].find(b => b.textContent?.trim() === 'Desactivar')!
    confirm.click()
    await flush()
    expect(action).toHaveBeenCalledWith({ id: 's1', is_active: true }, { is_active: false, activity_reason: 'Se fusionó' })
  })
})

describe('UiFormModal con activity', () => {
  it('agrega las pestañas General y Actividad, y la de actividad carga el historial', async () => {
    const Host = defineComponent({
      setup() {
        useZodForm(z.object({ name: zOptionalText() }), { initialValues: { name: '' } })
        return () => h(UiFormModal, {
          open: true,
          title: 'Editar unidad',
          activity: { entityType: 'units', entityId: 'u1' }
        }, { default: () => h('p', 'Campos') })
      }
    })
    await mountSuspended(Host, { attachTo: document.body })
    await flush()
    const tabs = [...document.body.querySelectorAll('[role="tab"]')].map(t => t.textContent?.trim())
    expect(tabs).toEqual(['General', 'Actividad'])
    expect(getMock).not.toHaveBeenCalled()
    ;(document.body.querySelectorAll('[role="tab"]')[1] as HTMLButtonElement).click()
    await flush()
    expect(getMock).toHaveBeenCalledWith('/activity', expect.objectContaining({
      params: expect.objectContaining({ entity_type: 'units', entity_id: 'u1' })
    }))
    expect(document.body.textContent).toContain('Duplicada')
  })

  it('sin activity no muestra pestañas', async () => {
    await mountSuspended(UiFormModal, { props: { open: true, title: 'Nueva unidad' }, attachTo: document.body })
    await flush()
    expect(document.body.querySelector('[role="tab"]')).toBeNull()
  })
})
