<script setup lang="ts">
/**
 * Vista previa (solo lectura) del reporte con la configuración actual de la
 * versión: secciones en orden, analitos en orden con tipo de resultado,
 * unidad, decimales y sus rangos de referencia activos formateados
 * (`buildReportPreview`). Lo inactivo queda fuera. Usa los datos que ya cargó
 * `useResultTemplateVersionContent` y consulta los rangos activos de cada
 * analito al mostrarse; se muestra bajo demanda para que cada apertura
 * refleje los últimos cambios del editor.
 */
import type { ResultTemplateVersionContent } from '../composables/useResultTemplateVersionContent'

const props = defineProps<{ content: ResultTemplateVersionContent }>()

const loading = ref(true)
const error = ref<string | null>(null)

/** Carga los rangos cuando los analitos están listos (y de nuevo si cambian). */
watch(
  () => [props.content.analytesLoading, props.content.templateAnalytes] as const,
  async ([analytesLoading]) => {
    if (analytesLoading) return
    loading.value = true
    error.value = null
    try {
      await props.content.loadReferenceRanges()
    } catch (err) {
      error.value = err instanceof Error && err.message ? err.message : 'No se pudieron cargar los rangos de referencia.'
    } finally {
      loading.value = false
    }
  },
  { immediate: true }
)

const groups = computed(() => buildReportPreview({
  sections: props.content.sections,
  analytes: props.content.templateAnalytes,
  ranges: props.content.referenceRanges,
  names: {
    analyte: id => props.content.analyteName(id),
    unit: id => props.content.unitSymbol(id),
    option: id => props.content.referenceName('expected_option_id', id)
  }
}))
</script>

<template>
  <div class="space-y-4" data-testid="report-preview">
    <UiAlert v-if="error" :message="error" />
    <div v-if="loading" class="flex justify-center py-6">
      <UiSpinner color="primary" label="Cargando vista previa" />
    </div>
    <p v-else-if="!groups.length" class="text-sm text-text-muted">
      La versión no tiene analitos activos: el reporte saldría vacío.
    </p>

    <section v-for="group in groups" :key="group.sectionId ?? 'none'" class="space-y-2">
      <h4 class="border-b border-border pb-1 text-sm font-semibold text-text">
        {{ group.name }}
      </h4>
      <table class="w-full text-left text-sm">
        <thead class="text-xs uppercase tracking-wide text-text-muted">
          <tr>
            <th scope="col" class="py-1 pr-3 font-medium">
              Analito
            </th>
            <th scope="col" class="py-1 pr-3 font-medium">
              Resultado
            </th>
            <th scope="col" class="py-1 font-medium">
              Valores de referencia
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in group.rows" :key="row.id" class="border-t border-border align-top" :class="{ 'text-text-muted': !row.reportable }">
            <th scope="row" class="py-2 pr-3 font-medium">
              {{ row.name }}
              <UiStatusBadge v-if="!row.reportable" variant="neutral" label="No reportable" class="ml-1" />
            </th>
            <td class="py-2 pr-3">
              {{ row.resultType }}
              <span v-if="row.unit" class="text-text-muted">· {{ row.unit }}</span>
              <span v-if="row.decimals !== null" class="text-text-muted">· {{ row.decimals }} dec.</span>
            </td>
            <td class="py-2">
              <ul v-if="row.ranges.length" class="space-y-0.5">
                <li v-for="line in row.ranges" :key="line">
                  {{ line }}
                </li>
              </ul>
              <span v-else class="text-text-muted">Sin rangos</span>
            </td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>
</template>
