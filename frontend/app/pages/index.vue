<script setup lang="ts">
definePageMeta({ layout: 'default' })
</script>

<template>
  <div class="space-y-6">
    <div>
      <h2 class="text-2xl font-semibold tracking-tight text-text">
        Dashboard
      </h2>
      <p class="mt-1 text-sm text-text-muted">
        Bienvenido al panel de administración de Vladimir.
      </p>
    </div>

    <UiCard>
      <p class="text-sm text-text-muted">
        Selecciona un módulo en el menú lateral para comenzar.
      </p>
    </UiCard>
  </div>
</template>
