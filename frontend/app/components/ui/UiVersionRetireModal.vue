<script setup lang="ts">
/**
 * Confirmación de retirar una versión (estado de `useConfirmAction`), común a
 * `UiVersionSection` (línea de tiempo del modal) y `UiVersionEditor` (página
 * del editor). Si el backend responde 409 `version_in_use`, muestra su
 * mensaje y la lista de exámenes que la usan (`versionInUseCodes`).
 */
import type { ConfirmActionView } from '#andromeda/composables/useConfirmAction'

const props = defineProps<{ state: ConfirmActionView }>()

const open = computed({
  get: () => props.state.open,
  set: (value: boolean) => {
    // eslint-disable-next-line vue/no-mutating-props -- estado reactivo compartido de useConfirmAction
    props.state.open = value
  }
})
const inUseCodes = computed(() => versionInUseCodes(props.state.errorCause))
</script>

<template>
  <UiConfirmModal
    v-model:open="open"
    title="Retirar versión"
    message="La versión retirada deja de estar disponible para nuevos exámenes. Esta acción no se puede deshacer."
    confirm-label="Retirar"
    :loading="state.loading"
    :error="state.error"
    :error-items="inUseCodes"
    error-items-label="Exámenes activos que la usan:"
    @confirm="state.confirm()"
  />
</template>
