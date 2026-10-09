<script setup lang="ts">
/**
 * Marco de los editores de versión (página propia, excepción a la regla de
 * modales): título "Versión N", volver a la entidad, carga / error, estado
 * de la versión con Publicar / Retirar (con confirmación), errores de esas
 * acciones (slot `#action-error` para detalles propios del módulo) y aviso
 * de solo lectura si ya no es borrador. El contenido (formularios de la
 * versión) va en el slot por defecto; envuélvelo en
 * `<fieldset :disabled="!editor.isDraft">` para bloquearlo fuera de draft.
 *
 * El estado viene de `useVersionEditor` (lo crea la página).
 */
import type { VersionEditorView } from '~/composables/useVersionEditor'

withDefaults(
  defineProps<{
    editor: VersionEditorView
    /** Ruta de vuelta (el listado del módulo; la entidad se abre en modal). */
    backTo: string
    backLabel?: string
    /** Nombre de la entidad, bajo el título. */
    subtitle?: string
    /** Motivo por el que no se puede publicar ahora (deshabilita Publicar y se muestra al lado). */
    publishBlockedReason?: string | null
  }>(),
  {
    backLabel: 'Volver',
    subtitle: undefined,
    publishBlockedReason: null
  }
)
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="text-xl font-semibold text-text">
          Versión {{ editor.version?.version_number ?? '' }}
        </h2>
        <p v-if="subtitle" class="mt-1 text-sm text-text-muted">
          {{ subtitle }}
        </p>
      </div>
      <UiButton :to="backTo" variant="secondary" size="sm">
        {{ backLabel }}
      </UiButton>
    </div>

    <div v-if="editor.loading" class="flex items-center gap-2 text-sm text-text-muted">
      <UiSpinner size="sm" color="primary" />
      <span>Cargando versión…</span>
    </div>

    <UiAlert v-else-if="editor.loadError" :message="editor.loadError" />

    <template v-else-if="editor.version">
      <div class="flex flex-wrap items-center gap-3">
        <UiVersionStatusBadge :status="editor.version.status" />
        <UiButton
          v-if="editor.isDraft"
          variant="primary"
          size="sm"
          :loading="editor.publishing"
          :disabled="Boolean(publishBlockedReason)"
          @click="editor.publish()"
        >
          Publicar
        </UiButton>
        <span v-if="editor.isDraft && publishBlockedReason" class="text-xs text-text-muted">
          {{ publishBlockedReason }}
        </span>
        <UiButton
          v-if="editor.isPublished"
          variant="danger-ghost"
          size="sm"
          @click="editor.retirement.ask(true)"
        >
          Retirar
        </UiButton>
      </div>

      <UiAlert
        v-if="editor.actionError"
        :title="$slots['action-error'] ? editor.actionError : undefined"
        :message="editor.actionError"
      >
        <template v-if="$slots['action-error']" #default>
          <slot name="action-error" :details="editor.actionErrorDetails" />
        </template>
      </UiAlert>

      <UiAlert v-if="!editor.isDraft" variant="warning" message="Esta versión ya no es un borrador: su contenido es de solo lectura." />

      <slot />
    </template>

    <UiVersionRetireModal :state="editor.retirement" />
  </div>
</template>
