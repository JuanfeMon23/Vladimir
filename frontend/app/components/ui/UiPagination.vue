<script setup lang="ts">
/**
 * Pie de paginación del núcleo ("Página X de Y · N registros" + Anterior /
 * Siguiente). Lo usan `UiDataTable` y `UiExpandableList`; un listado que no
 * use ninguno de los dos lo usa directo en vez de copiar los botones.
 */
const props = defineProps<{
  /** Página actual (1-based). */
  page: number
  pageSize: number
  total: number
}>()

const emit = defineEmits<{
  'update:page': [page: number]
}>()

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / Math.max(1, props.pageSize))))

function goToPage(next: number) {
  if (next < 1 || next > totalPages.value) return
  emit('update:page', next)
}
</script>

<template>
  <nav
    class="flex flex-wrap items-center justify-between gap-2 px-1 pt-2 text-sm text-text-muted"
    aria-label="Paginación"
  >
    <span>Página {{ page }} de {{ totalPages }} · {{ total }} registros</span>
    <div class="flex gap-2">
      <UiButton variant="secondary" size="sm" :disabled="page <= 1" @click="goToPage(page - 1)">
        Anterior
      </UiButton>
      <UiButton variant="secondary" size="sm" :disabled="page >= totalPages" @click="goToPage(page + 1)">
        Siguiente
      </UiButton>
    </div>
  </nav>
</template>
