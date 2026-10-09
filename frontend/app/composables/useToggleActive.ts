import type { ActivityChange } from '~/types/activity'

export interface UseToggleActiveOptions {
  /** Mensaje si el error no trae uno propio. */
  errorMessage?: string
}

/**
 * Desactivar / reactivar un elemento con motivo opcional, confirmado en
 * `UiToggleActiveModal` (reemplaza los "Eliminar": nada se elimina). La
 * acción recibe el objetivo y el cuerpo `{ is_active, activity_reason }`
 * para el PATCH.
 *
 * ```ts
 * const toggle = useToggleActive((section: SectionRead, change) =>
 *   api.updateSection(…, section.id, change))
 * // fila:  <UiButton @click="toggle.ask(section)">Desactivar</UiButton>
 * // modal: <UiToggleActiveModal :state="toggle" :name="toggle.target?.name" />
 * ```
 */
export function useToggleActive<T extends { is_active: boolean }>(
  action: (target: T, change: ActivityChange) => Promise<unknown>,
  options: UseToggleActiveOptions = {}
) {
  const reason = ref('')

  const confirmation = useConfirmAction<T>(
    target => action(target, { is_active: !target.is_active, activity_reason: reason.value.trim() || null }),
    { errorMessage: options.errorMessage ?? 'No se pudo cambiar el estado.' }
  )

  function ask(target: T) {
    reason.value = ''
    confirmation.ask(target)
  }

  /** Estado al que pasará el objetivo (`true` = reactivar). */
  const nextActive = computed(() => (confirmation.target ? !confirmation.target.is_active : false))

  return reactive({
    open: toRef(confirmation, 'open'),
    target: toRef(confirmation, 'target'),
    loading: toRef(confirmation, 'loading'),
    error: toRef(confirmation, 'error'),
    reason,
    nextActive,
    ask,
    confirm: () => confirmation.confirm()
  })
}

export type ToggleActiveState = ReturnType<typeof useToggleActive>

/** Lo que `UiToggleActiveModal` lee y escribe del estado (independiente del tipo del objetivo). */
export type ToggleActiveView = Pick<ToggleActiveState, 'open' | 'loading' | 'error' | 'reason' | 'nextActive' | 'confirm'>
