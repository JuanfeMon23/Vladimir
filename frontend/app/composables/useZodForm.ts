import { toTypedSchema } from '@vee-validate/zod'
import { useForm } from 'vee-validate'
import type { WatchSource } from 'vue'
import type { z } from 'zod'

export interface UseZodFormOptions<TSchema extends z.ZodTypeAny> {
  /**
   * Valores iniciales. Debe incluir TODOS los campos del formulario (se usan
   * para mapear errores del backend). Puede ser una función (p. ej. a partir
   * de la entidad que edita un modal): se reevalúa en cada `reset()`.
   */
  initialValues: z.input<TSchema> | (() => z.input<TSchema>)
  /** Claves del backend → rutas del formulario, cuando difieren (ver `mapApiErrorToForm`). */
  fieldMap?: Record<string, string>
  /**
   * Cuando esta fuente pasa a `true`, el formulario se reinicia con
   * `initialValues` (y se limpia `formError`). Pensado para formularios en
   * modal: `resetOn: open` recarga los valores de la entidad al abrir.
   */
  resetOn?: WatchSource<boolean>
}

/**
 * Patrón obligatorio de formularios del panel: un schema zod por formulario +
 * vee-validate. Envuelve `useForm` y agrega:
 * - `formError`: error general (para `UiAlert`), p. ej. un 409 sin campo.
 * - `applyApiError(err)`: vuelca un `ApiRequestError` del backend a errores
 *   por campo (`UiFormField` los muestra) o al error general.
 * - `reset(values?)`: reinicia el formulario (también automático con `resetOn`).
 * - `submit(handler)`: `handleSubmit` que solo llama al handler si el schema
 *   valida, limpia `formError` y aplica `applyApiError` si el handler lanza.
 *   Mientras corre, `isSubmitting` es `true` (pásalo a `UiButton :loading`).
 *
 * Los campos se declaran con `<UiFormField name="campo">` + un control del
 * núcleo dentro, sin `v-model`.
 */
export function useZodForm<TSchema extends z.ZodTypeAny>(
  schema: TSchema,
  options: UseZodFormOptions<TSchema>
) {
  const resolveInitial = () =>
    typeof options.initialValues === 'function'
      ? (options.initialValues as () => z.input<TSchema>)()
      : options.initialValues

  // Sin `cast`: vee-validate reemplaza los valores iniciales (y los de
  // `resetForm`) por la SALIDA del schema cuando validan ('' → null, texto
  // JSON → objeto, '' → null en un enum de select…). El formulario debe
  // guardar la ENTRADA de los controles; la salida solo llega al `submit`.
  const { cast: _cast, ...validationSchema } = toTypedSchema(schema)

  const form = useForm({
    validationSchema,
    initialValues: resolveInitial()
  })

  const formError = ref<string | null>(null)

  /** Reinicia valores (a `values` o a `initialValues`), errores, `touched` y `formError`. */
  function reset(values?: z.input<TSchema>) {
    formError.value = null
    type ResetValues = NonNullable<Parameters<typeof form.resetForm>[0]>['values']
    form.resetForm({ values: (values ?? resolveInitial()) as ResetValues })
  }

  if (options.resetOn) {
    watch(options.resetOn, (active) => {
      if (active) reset()
    })
  }

  function applyApiError(err: unknown) {
    const { formError: general, fieldErrors } = mapApiErrorToForm(err, {
      fields: Object.keys(form.values as Record<string, unknown>),
      fieldMap: options.fieldMap
    })
    formError.value = general
    for (const [path, message] of Object.entries(fieldErrors)) {
      form.setFieldError(path as Parameters<typeof form.setFieldError>[0], message)
    }
  }

  function submit(handler: (values: z.output<TSchema>) => unknown) {
    return form.handleSubmit(async (values) => {
      formError.value = null
      try {
        await handler(values as z.output<TSchema>)
      } catch (err) {
        applyApiError(err)
      }
    })
  }

  return { ...form, formError, applyApiError, submit, reset }
}
