import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useDebouncedRef } from './useDebouncedRef'

beforeEach(() => { vi.useFakeTimers() })
afterEach(() => { vi.useRealTimers() })

describe('useDebouncedRef', () => {
  it('arranca con el valor de origen', () => {
    const source = ref('a')
    expect(useDebouncedRef(source, 300).debounced.value).toBe('a')
  })

  it('refleja el cambio solo después del retardo', async () => {
    const source = ref('')
    const { debounced } = useDebouncedRef(source, 300)
    source.value = 'h'
    await nextTick()
    vi.advanceTimersByTime(299)
    expect(debounced.value).toBe('')
    vi.advanceTimersByTime(1)
    expect(debounced.value).toBe('h')
  })

  it('escrituras seguidas reinician el temporizador y solo cuenta la última', async () => {
    const source = ref('')
    const { debounced } = useDebouncedRef(source, 300)
    source.value = 'h'
    await nextTick()
    vi.advanceTimersByTime(200)
    source.value = 'he'
    await nextTick()
    vi.advanceTimersByTime(200)
    expect(debounced.value).toBe('')
    vi.advanceTimersByTime(100)
    expect(debounced.value).toBe('he')
  })

  it('flush aplica el valor actual de inmediato y cancela el pendiente', async () => {
    const source = ref('')
    const { debounced, flush } = useDebouncedRef(source, 300)
    source.value = 'abc'
    await nextTick()
    flush()
    expect(debounced.value).toBe('abc')
    vi.advanceTimersByTime(1000)
    expect(debounced.value).toBe('abc')
  })

  it('cancel descarta el cambio pendiente', async () => {
    const source = ref('')
    const { debounced, cancel } = useDebouncedRef(source, 300)
    source.value = 'abc'
    await nextTick()
    cancel()
    vi.advanceTimersByTime(1000)
    expect(debounced.value).toBe('')
  })
})
