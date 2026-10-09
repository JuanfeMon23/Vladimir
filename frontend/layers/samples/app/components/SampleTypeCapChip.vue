<script setup lang="ts">
/**
 * Chip visual del tipo de muestra: punto de color de la tapa (si
 * `cap-color-hex` viene del backend) + nombre. Específico del dominio de
 * `samples` (tubo/tapa), no se generaliza al núcleo.
 */
defineProps<{
  label: string
  capColorHex?: string | null
}>()
</script>

<template>
  <span class="inline-flex items-center gap-1.5 text-sm text-text">
    <span
      v-if="capColorHex"
      class="h-3 w-3 shrink-0 rounded-full border border-border-strong"
      :style="{ backgroundColor: capColorHex }"
      aria-hidden="true"
    />
    <span v-else class="h-3 w-3 shrink-0 rounded-full border border-dashed border-border-strong" aria-hidden="true" />
    {{ label }}
  </span>
</template>
