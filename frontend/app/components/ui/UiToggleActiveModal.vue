<script setup lang="ts">
/**
 * Confirmación de desactivar / reactivar con motivo opcional (estado de
 * `useToggleActive`). Reemplaza los "Eliminar": nada se elimina, se
 * desactiva. Desactivar es `danger`; reactivar, `primary`.
 */
import type { ToggleActiveView } from '~/composables/useToggleActive'

const props = defineProps<{
  state: ToggleActiveView
  /** Nombre legible del objetivo (va en el mensaje). */
  name?: string
  /** Sustantivo con artículo para el título, p. ej. "la sección" → "Desactivar la sección". */
  noun?: string
  /** Texto adicional al desactivar (p. ej. qué deja de pasar). */
  deactivateHint?: string
}>()

const reasonId = useId()
const verb = computed(() => (props.state.nextActive ? 'Reactivar' : 'Desactivar'))
const title = computed(() => `${verb.value} ${props.noun ?? 'el elemento'}`)
const message = computed(() => {
  const subject = props.name ? `«${props.name}»` : 'El elemento'
  if (props.state.nextActive) return `${subject} volverá al estado activo.`
  return `${subject} pasará a estado inactivo (no se elimina; se puede reactivar).${props.deactivateHint ? ` ${props.deactivateHint}` : ''}`
})

const open = computed({
  get: () => props.state.open,
  set: (value: boolean) => {
    // eslint-disable-next-line vue/no-mutating-props -- estado reactivo compartido de useToggleActive
    props.state.open = value
  }
})
const reason = computed({
  get: () => props.state.reason,
  set: (value: string) => {
    // eslint-disable-next-line vue/no-mutating-props -- estado reactivo compartido de useToggleActive
    props.state.reason = value
  }
})
</script>

<template>
  <UiConfirmModal
    v-model:open="open"
    :title="title"
    :message="message"
    :confirm-label="verb"
    :variant="state.nextActive ? 'primary' : 'danger'"
    :loading="state.loading"
    :error="state.error"
    @confirm="state.confirm()"
  >
    <template #extra>
      <UiFormField :field-id="reasonId" label="Motivo" hint="Opcional. Queda en el historial de actividad.">
        <UiTextarea v-model="reason" :rows="2" maxlength="255" />
      </UiFormField>
    </template>
  </UiConfirmModal>
</template>
