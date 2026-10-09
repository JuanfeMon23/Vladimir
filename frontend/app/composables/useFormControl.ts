import type { ComputedRef, InjectionKey, Ref } from 'vue'

/**
 * Contexto que `UiFormField` provee a su control hijo (`UiTextInput`,
 * `UiTextarea`, `UiSelect`, `UiCheckbox`). Permite que el control:
 * - herede `id`, `aria-invalid` y `aria-describedby` sin repetirlos;
 * - cuando `UiFormField` recibe `name`, se enlace solo al campo de
 *   vee-validate (valor, blur y error) sin `v-model` en cada formulario.
 */
export interface UiFormFieldContext {
  id: ComputedRef<string>
  invalid: ComputedRef<boolean>
  describedBy: ComputedRef<string | undefined>
  /** Solo presente si `UiFormField` tiene `name` (modo vee-validate). */
  field?: {
    value: Ref<unknown>
    setValue: (value: unknown) => void
    handleBlur: (event?: Event) => void
  }
}

export const UI_FORM_FIELD_KEY: InjectionKey<UiFormFieldContext> = Symbol('UiFormField')

interface FormControlProps<V> {
  id?: string
  modelValue?: V
  invalid?: boolean
}

/**
 * Lógica compartida por los controles del núcleo. Resuelve el valor y los
 * atributos de accesibilidad combinando las props explícitas (prioridad) con
 * el contexto de `UiFormField`.
 *
 * - Modo controlado (`v-model` / `:model-value`): igual que antes del rediseño.
 * - Modo vee-validate (`<UiFormField name="...">`): sin `model-value`, lee y
 *   escribe el valor del campo del formulario.
 */
export function useFormControl<V>(
  props: FormControlProps<V>,
  emitUpdate: (value: V) => void
) {
  const ctx = inject(UI_FORM_FIELD_KEY, null)

  const controlId = computed(() => props.id ?? ctx?.id.value)
  const isInvalid = computed(() => props.invalid || ctx?.invalid.value || false)
  const describedBy = computed(() => ctx?.describedBy.value)

  const value = computed<V | undefined>(() => {
    if (props.modelValue !== undefined) return props.modelValue
    return ctx?.field?.value.value as V | undefined
  })

  function update(next: V) {
    emitUpdate(next)
    ctx?.field?.setValue(next)
  }

  function onBlur(event: Event) {
    ctx?.field?.handleBlur(event)
  }

  return { controlId, isInvalid, describedBy, value, update, onBlur }
}
