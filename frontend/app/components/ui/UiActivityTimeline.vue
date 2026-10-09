<script setup lang="ts">
/**
 * Historial de activación/desactivación de una entidad (`useActivity`):
 * línea de tiempo con fecha-hora local, acción (chip Activado/Desactivado)
 * y motivo. Carga al montarse; `UiFormModal :activity` la pone en su pestaña
 * "Actividad" (y `UiTabs` la monta solo al visitarla).
 *
 * Con `events` pinta esa lista fija y no consulta la API (referencia viva
 * `/_design`, tests).
 */
import type { ActivityEntityType, ActivityEventRead } from '~/types/activity'

const props = withDefaults(
  defineProps<{
    entityType: ActivityEntityType
    entityId?: string | null
    /** Eventos fijos (no consulta la API). */
    events?: ActivityEventRead[]
    emptyMessage?: string
  }>(),
  { entityId: null, events: undefined, emptyMessage: 'Sin cambios de estado registrados.' }
)

const activity = useActivity(() => props.entityType, () => (props.events ? null : props.entityId))
const shown = computed(() => props.events ?? activity.events)
</script>

<template>
  <div class="space-y-3">
    <UiAlert v-if="activity.error" :message="activity.error" />

    <div
      v-if="activity.loading && shown.length === 0"
      class="flex items-center gap-2 rounded-lg border border-border px-4 py-4 text-sm text-text-muted"
    >
      <UiSpinner size="sm" color="primary" />
      <span>Cargando actividad…</span>
    </div>

    <p
      v-else-if="!activity.error && shown.length === 0"
      class="rounded-lg border border-dashed border-border px-4 py-4 text-center text-sm text-text-muted"
    >
      {{ emptyMessage }}
    </p>

    <ol v-else class="relative space-y-4 border-l-2 border-default-200 pl-5" aria-label="Historial de actividad">
      <li v-for="event in shown" :key="event.id" class="relative">
        <span
          class="absolute -left-[1.6rem] top-1.5 h-3 w-3 rounded-full ring-4 ring-surface"
          :class="event.action === 'activated' ? 'bg-success-500' : 'bg-danger-500'"
          aria-hidden="true"
        />
        <div class="flex flex-wrap items-center gap-2">
          <UiStatusBadge
            :variant="event.action === 'activated' ? 'success' : 'danger'"
            :label="ACTIVITY_ACTION_LABELS[event.action]"
          />
          <time :datetime="event.occurred_at" class="text-sm text-text-muted">
            {{ formatDateTime(event.occurred_at) }}
          </time>
        </div>
        <p class="mt-1 text-sm" :class="event.reason ? 'text-text' : 'text-text-muted'">
          {{ event.reason || 'Sin motivo.' }}
        </p>
      </li>
    </ol>

    <UiButton
      v-if="!events && activity.hasMore"
      variant="secondary"
      size="sm"
      :loading="activity.loading"
      @click="activity.loadMore()"
    >
      Cargar más
    </UiButton>
  </div>
</template>
