<script setup lang="ts" generic="T extends LabTestAssignmentRow">
/**
 * Marco de una pestaña de asignaciones del examen (precondiciones, tipos de
 * muestra, documentos a firmar): sección con su propio `<form>` (fuera del
 * form principal del modal), avisos de carga / error / guardado, lista de
 * filas (`buildLabTestAssignmentRows`) con un checkbox por fila
 * (`UiItemList`, filas en los slots) y el botón Guardar. El `useZodForm` de
 * la pestaña vive en el componente que lo usa; sus `UiFormField name` de los
 * slots lo heredan.
 *
 * Reglas de activación: el toggle "Mostrar inactivos" muestra el historial de
 * asignaciones quitadas; las filas de elementos desactivados se atenúan y
 * llevan su chip.
 *
 * Cada fila que tiene (o tuvo) asignación muestra un botón "Actividad" que
 * despliega el historial de activación de esa asignación
 * (`UiActivityTimeline` con `activity-entity-type`).
 */
import type { ActivityEntityType } from '~/types/activity'
import type { LabTestAssignmentRow } from '../utils/assignmentRows'

const props = withDefaults(
  defineProps<{
    title: string
    description?: string
    /** Tabla de la asignación para el historial (`lab_test_preconditions`…). */
    activityEntityType: ActivityEntityType
    items: T[]
    loading?: boolean
    loadError?: string | null
    formError?: string | null
    /** Mensaje de éxito tras guardar (`null` si no hay). */
    savedMessage?: string | null
    submitting?: boolean
    submitLabel?: string
    emptyMessage?: string
  }>(),
  {
    description: undefined,
    loading: false,
    loadError: null,
    formError: null,
    savedMessage: null,
    submitting: false,
    submitLabel: 'Guardar',
    emptyMessage: 'No hay registros activos en el catálogo.'
  }
)

const emit = defineEmits<{
  submit: []
}>()

const showInactive = ref(false)
/** Filas con el historial desplegado (por id de asignación). */
const openActivity = ref(new Set<string>())
function toggleActivity(linkId: string) {
  const next = new Set(openActivity.value)
  if (next.has(linkId)) next.delete(linkId)
  else next.add(linkId)
  openActivity.value = next
}

const visibleItems = computed(() => visibleLabTestAssignmentRows(props.items, showInactive.value) as T[])
</script>

<template>
  <UiSection :title="title" :description="description">
    <template #actions>
      <UiCheckbox v-model="showInactive" label="Mostrar inactivos" />
    </template>

    <form class="space-y-4" novalidate @submit.prevent="emit('submit')">
      <UiAlert v-if="loadError" :message="loadError" />
      <UiAlert v-if="formError" :message="formError" />
      <UiAlert v-if="savedMessage" variant="success" :message="savedMessage" />

      <UiItemList
        :items="visibleItems"
        :row-key="(row: T) => row.id"
        :loading="loading"
        :empty-message="emptyMessage"
        :inactive="(row: T) => row.elementInactive || !row.selectable"
      >
        <template #default="{ item }">
          <slot :item="item" />
          <div v-if="item.linkId && openActivity.has(item.linkId)" class="mt-3 pl-7">
            <UiActivityTimeline
              :entity-type="activityEntityType"
              :entity-id="item.linkId"
              empty-message="Sin cambios de estado de esta asignación."
            />
          </div>
        </template>
        <template #trailing="{ item }">
          <UiStatusBadge v-if="item.elementInactive" :active="false" />
          <UiStatusBadge v-if="showInactive && item.linkInactive" variant="neutral" label="Asignación quitada" />
          <slot name="trailing" :item="item" />
          <UiButton
            v-if="item.linkId"
            variant="ghost"
            size="sm"
            :aria-expanded="openActivity.has(item.linkId)"
            @click="toggleActivity(item.linkId)"
          >
            {{ openActivity.has(item.linkId) ? 'Ocultar actividad' : 'Actividad' }}
          </UiButton>
        </template>
      </UiItemList>

      <UiButton type="submit" :loading="submitting" :disabled="loading || Boolean(loadError)">
        {{ submitLabel }}
      </UiButton>
    </form>
  </UiSection>
</template>
