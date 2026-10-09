import { mountSuspended } from '@nuxt/test-utils/runtime'
import { nextTick } from 'vue'
import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import UiSearchInput from './UiSearchInput.vue'

enableAutoUnmount(afterEach)
beforeEach(() => { vi.useFakeTimers() })
afterEach(() => { vi.useRealTimers() })

async function mountInput(props: Record<string, unknown> = {}) {
  return mountSuspended(UiSearchInput, { props: { modelValue: '', ...props } })
}

type Wrapper = Awaited<ReturnType<typeof mountInput>>

const type = (wrapper: Wrapper, value: string) => wrapper.find('input').setValue(value)
const emitted = (wrapper: Wrapper) => wrapper.emitted('update:modelValue')?.map(e => e[0]) ?? []
const inputValue = (wrapper: Wrapper) => (wrapper.find('input').element as HTMLInputElement).value

describe('UiSearchInput', () => {
  it('es un buscador accesible: role search y label asociado', async () => {
    const wrapper = await mountInput({ label: 'Buscar personal' })
    expect(wrapper.find('[role="search"]').exists()).toBe(true)
    const input = wrapper.find('input')
    expect(wrapper.find(`label[for="${input.attributes('id')}"]`).text()).toBe('Buscar personal')
  })

  it('muestra el placeholder del módulo y limita a 100 caracteres', async () => {
    const wrapper = await mountInput({ placeholder: 'Buscar por código o nombre…' })
    const input = wrapper.find('input')
    expect(input.attributes('placeholder')).toBe('Buscar por código o nombre…')
    expect(input.attributes('maxlength')).toBe('100')
  })

  it('emite el texto solo tras el debounce (300 ms)', async () => {
    const wrapper = await mountInput()
    await type(wrapper, 'her')
    vi.advanceTimersByTime(299)
    expect(emitted(wrapper)).toEqual([])
    vi.advanceTimersByTime(1)
    await nextTick()
    expect(emitted(wrapper)).toEqual(['her'])
  })

  it('escribir seguido emite una sola vez el último valor', async () => {
    const wrapper = await mountInput()
    await type(wrapper, 'h')
    vi.advanceTimersByTime(200)
    await type(wrapper, 'he')
    vi.advanceTimersByTime(299)
    expect(emitted(wrapper)).toEqual([])
    vi.advanceTimersByTime(1)
    await nextTick()
    expect(emitted(wrapper)).toEqual(['he'])
  })

  it('Enter emite de inmediato', async () => {
    const wrapper = await mountInput()
    await type(wrapper, 'abc')
    await wrapper.find('input').trigger('keydown', { key: 'Enter' })
    expect(emitted(wrapper)).toEqual(['abc'])
  })

  it('el botón limpiar vacía el campo, emite de inmediato y solo aparece con texto', async () => {
    const wrapper = await mountInput({ modelValue: 'abc' })
    expect(inputValue(wrapper)).toBe('abc')
    const clear = wrapper.find('button[aria-label="Limpiar búsqueda"]')
    expect(clear.exists()).toBe(true)
    await clear.trigger('click')
    expect(inputValue(wrapper)).toBe('')
    expect(emitted(wrapper)).toEqual([''])
    expect(wrapper.find('button[aria-label="Limpiar búsqueda"]').exists()).toBe(false)
  })

  it('Escape limpia el campo y emite de inmediato', async () => {
    const wrapper = await mountInput({ modelValue: 'abc' })
    await wrapper.find('input').trigger('keydown', { key: 'Escape' })
    expect(inputValue(wrapper)).toBe('')
    expect(emitted(wrapper)).toEqual([''])
  })

  it('refleja al instante un cambio externo de v-model (p. ej. Limpiar búsqueda del estado vacío)', async () => {
    const wrapper = await mountInput({ modelValue: 'abc' })
    await wrapper.setProps({ modelValue: '' })
    expect(inputValue(wrapper)).toBe('')
    vi.advanceTimersByTime(1000)
    expect(emitted(wrapper)).toEqual([])
  })

  it('con loading marca aria-busy', async () => {
    const wrapper = await mountInput({ loading: true })
    expect(wrapper.find('input').attributes('aria-busy')).toBe('true')
  })
})
