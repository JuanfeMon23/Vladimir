<script setup lang="ts">
/**
 * Confirmación de una acción (destructiva por defecto: retirar, eliminar,
 * desactivar): `UiModal size="sm"` + mensaje + error opcional + pie
 * Cancelar / Confirmar. Reemplaza `window.confirm` y el modal de confirmación
 * escrito a mano en cada vista (skill `frontend-reusable-ui`).
 *
 * La acción la ejecuta quien lo usa al recibir `confirm`; mientras
 * `loading`, el modal no se cierra con Esc/backdrop. El que lo usa cierra el
 * modal (`open = false`) cuando la acción termina bien.
 *
 * Slot `#extra`: campos bajo el mensaje (p. ej. el motivo de
 * `UiToggleActiveModal`).
 *
 * `error-items`: lista que acompaña al error (p. ej. los exámenes que usan
 * una versión que no se puede retirar), con su rótulo `error-items-label`.
 */
const open = defineModel<boolean>('open', { required: true })

withDefaults(
  defineProps<{
    title: string
    message?: string
    confirmLabel?: string
    cancelLabel?: string
    /** `danger` (destructiva) o `primary` (confirmación neutra). */
    variant?: 'danger' | 'primary'
    loading?: boolean
    error?: string | null
    errorItems?: readonly string[]
    errorItemsLabel?: string
  }>(),
  {
    message: undefined,
    confirmLabel: 'Confirmar',
    cancelLabel: 'Cancelar',
    variant: 'danger',
    loading: false,
    error: null,
    errorItems: () => [],
    errorItemsLabel: undefined
  }
)

const emit = defineEmits<{
  confirm: []
}>()
</script>

<template>
  <UiModal v-model:open="open" :title="title" size="sm" :dismissable="!loading">
    <div class="space-y-3">
      <UiAlert v-if="error && errorItems.length" :title="error">
        <p v-if="errorItemsLabel">
          {{ errorItemsLabel }}
        </p>
        <ul class="mt-1 list-disc pl-5">
          <li v-for="item in errorItems" :key="item">
            {{ item }}
          </li>
        </ul>
      </UiAlert>
      <UiAlert v-else-if="error" :message="error" />
      <p v-if="message || $slots.default" class="text-sm text-text-muted">
        <slot>{{ message }}</slot>
      </p>
      <!-- Campos adicionales de la confirmación (p. ej. motivo en UiToggleActiveModal). -->
      <slot name="extra" />
    </div>

    <template #footer="{ close }">
      <UiButton variant="secondary" :disabled="loading" @click="close">
        {{ cancelLabel }}
      </UiButton>
      <UiButton :variant="variant" :loading="loading" @click="emit('confirm')">
        {{ confirmLabel }}
      </UiButton>
    </template>
  </UiModal>
</template>
