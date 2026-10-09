import { mountSuspended } from '@nuxt/test-utils/runtime'
import { describe, expect, it, vi } from 'vitest'
import { defineComponent, h, nextTick, ref } from 'vue'
import { z } from 'zod'
import { ApiRequestError } from './useApi'
import { useZodForm } from './useZodForm'

/** Monta un componente mínimo que usa `useZodForm` y devuelve su estado. */
async function setupForm<S extends z.ZodTypeAny>(
  schema: S,
  options: Parameters<typeof useZodForm<S>>[1]
) {
  let form!: ReturnType<typeof useZodForm<S>>
  const Host = defineComponent({
    setup() {
      form = useZodForm(schema, options)
      return () => h('div')
    }
  })
  await mountSuspended(Host)
  return form
}

const flush = async () => {
  for (let i = 0; i < 5; i++) await nextTick()
  await new Promise(resolve => setTimeout(resolve, 0))
}

describe('useZodForm', () => {
  // Regresión: con el `cast` de `toTypedSchema`, vee-validate reemplazaba los
  // valores iniciales por la SALIDA del schema ('' → null). Un campo como
  // `expected_boolean` (z.enum(['', 'true', 'false'])) pasaba a `null`, ya no
  // validaba y el modal de rangos de referencia nunca enviaba.
  it('conserva la entrada de los controles y envía aunque un campo no renderizado transforme \'\' → null', async () => {
    const schema = z.object({
      name: zOptionalText(),
      expected_boolean: z.enum(['', 'true', 'false']).optional().transform(v => (v ? v === 'true' : null))
    })
    const form = await setupForm(schema, { initialValues: { name: '', expected_boolean: '' } })
    const handler = vi.fn()

    await form.submit(handler)()
    await flush()

    expect(form.values.expected_boolean).toBe('')
    expect(form.values.name).toBe('')
    expect(handler).toHaveBeenCalledWith({ name: null, expected_boolean: null })
  })

  it('no llama al handler si el schema no valida', async () => {
    const form = await setupForm(z.object({ code: zRequiredText('El código es obligatorio.') }), {
      initialValues: { code: '' }
    })
    const handler = vi.fn()
    await form.submit(handler)()
    await flush()
    expect(handler).not.toHaveBeenCalled()
    expect(form.errors.value.code).toBe('El código es obligatorio.')
  })

  it('si el handler lanza un AppError, lo vuelca a errores por campo o a formError', async () => {
    const form = await setupForm(z.object({ code: zRequiredText('x') }), { initialValues: { code: 'A' } })

    await form.submit(() => {
      throw new ApiRequestError({ code: 'conflict', message: 'Código duplicado.', details: { code: 'A' } }, 409)
    })()
    await flush()
    expect(form.errors.value.code).toBe('Código duplicado.')
    expect(form.formError.value).toBeNull()

    await form.submit(() => {
      throw new ApiRequestError({ code: 'reference_range_overlap', message: 'Se solapa.', details: { overlapping_id: 'r' } }, 422)
    })()
    await flush()
    expect(form.formError.value).toBe('Se solapa.')
  })

  it('resetOn recarga los valores iniciales (función) y limpia formError al abrir', async () => {
    const open = ref(false)
    const source = ref('primero')
    const form = await setupForm(z.object({ name: zOptionalText() }), {
      initialValues: () => ({ name: source.value }),
      resetOn: open
    })
    form.formError.value = 'viejo'
    source.value = 'segundo'
    open.value = true
    await flush()
    expect(form.values.name).toBe('segundo')
    expect(form.formError.value).toBeNull()
  })
})
