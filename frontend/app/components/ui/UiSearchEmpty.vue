<script setup lang="ts">
/**
 * Estado vacío de una búsqueda sin coincidencias ("Sin resultados para «x»" +
 * botón para limpiarla), distinto del estado "no hay datos". Lo usan
 * `UiDataTable` y `UiExpandableList` cuando reciben `search-term`.
 */
defineProps<{ term: string }>()
const emit = defineEmits<{ clear: [] }>()
</script>

<template>
  <div class="flex flex-col items-center gap-3">
    <p class="text-text-muted">
      Sin resultados para «<span class="font-medium text-text">{{ term }}</span>»
    </p>
    <UiButton variant="secondary" size="sm" @click="emit('clear')">
      Limpiar búsqueda
    </UiButton>
  </div>
</template>
