<script setup lang="ts">
/**
 * Modal de formulario de entidad (crear / ver-editar desde el listado).
 * Generaliza el patrón repetido en todas las layers: `UiModal` + `<form>` +
 * `UiAlert` del `formError` + pie "Cancelar / Guardar" enlazado al form por
 * `form="<id>"`, sin cierre por Esc/backdrop mientras se guarda.
 *
 * El formulario (zod + vee-validate) vive en el componente de la layer que
 * llama a `useZodForm`; los `<UiFormField name>` van en el slot por defecto
 * (heredan el contexto del form porque el slot se renderiza con el
 * componente de la layer como ancestro).
 *
 * Slot `#extra`: contenido del modal FUERA del `<form>` (sub-recursos de la
 * entidad con sus propios formularios, p. ej. encargado de un área o ítems
 * de una precondición). Un `<form>` no puede anidar otro `<form>`.
 *
 * Con `tabs` (detalle grande, p. ej. un examen): el contenido se reparte en
 * `UiTabs`. La pestaña `form-tab` (la primera por defecto) contiene el
 * `<form>` con el slot por defecto; cada otra pestaña renderiza el slot con
 * su `key` (fuera del form, con sus propios formularios). El botón Guardar
 * del pie solo aparece en la pestaña del form; al abrir se vuelve a ella.
 *
 * Con `activity` (entidad con `is_active`, en modo ver/editar): agrega la
 * pestaña "Actividad" (`UiActivityTimeline`). Si no había pestañas, el form y
 * el `#extra` quedan en una pestaña "General". La clave `activity` está
 * reservada.
 */
import type { ActivityEntityType } from '~/types/activity'
import type { UiModalSize } from './UiModal.vue'
import type { UiTab } from './UiTabs.vue'

const open = defineModel<boolean>('open', { required: true })

const props = withDefaults(
  defineProps<{
    title: string
    description?: string
    size?: UiModalSize
    /** `isSubmitting` de `useZodForm`: spinner en Guardar y bloqueo de cierre. */
    submitting?: boolean
    /** `formError` de `useZodForm`. */
    formError?: string | null
    submitLabel?: string
    cancelLabel?: string
    /** Pestañas del detalle; sin ellas, el modal es un formulario simple. */
    tabs?: UiTab[]
    /** Pestaña que contiene el formulario principal (por defecto, la primera). */
    formTab?: string
    /** Nombre accesible de la lista de pestañas. */
    tabsLabel?: string
    /** Historial de activación de la entidad (pestaña "Actividad"); solo al ver/editar. */
    activity?: { entityType: ActivityEntityType, entityId: string } | null
  }>(),
  {
    description: undefined,
    size: 'md',
    submitting: false,
    formError: null,
    submitLabel: 'Guardar',
    cancelLabel: 'Cancelar',
    tabs: undefined,
    formTab: undefined,
    tabsLabel: 'Secciones',
    activity: null
  }
)

const emit = defineEmits<{
  submit: []
}>()

const formId = useId()

const ACTIVITY_TAB: UiTab = { key: 'activity', label: 'Actividad' }
const allTabs = computed<UiTab[] | undefined>(() => {
  if (!props.activity) return props.tabs
  return [...(props.tabs?.length ? props.tabs : [{ key: 'general', label: 'General' }]), ACTIVITY_TAB]
})
const hasTabs = computed(() => Boolean(allTabs.value?.length))
const resolvedFormTab = computed(() => props.formTab ?? allTabs.value?.[0]?.key ?? '')
const activeTab = ref(resolvedFormTab.value)
watch(open, (isOpen) => {
  if (isOpen) activeTab.value = resolvedFormTab.value
})
const showSubmit = computed(() => !hasTabs.value || activeTab.value === resolvedFormTab.value)
</script>

<template>
  <UiModal
    v-model:open="open"
    :title="title"
    :description="description"
    :size="size"
    :dismissable="!submitting"
  >
    <div class="space-y-6">
      <UiTabs v-if="hasTabs && allTabs" v-model="activeTab" :tabs="allTabs" :aria-label="tabsLabel">
        <template v-for="tab in allTabs" :key="tab.key" #[tab.key]>
          <div v-if="tab.key === resolvedFormTab" class="space-y-6">
            <form
              :id="formId"
              class="space-y-4"
              novalidate
              @submit.prevent="emit('submit')"
            >
              <UiAlert v-if="formError" :message="formError" />
              <slot />
            </form>
            <slot name="extra" />
          </div>
          <UiActivityTimeline
            v-else-if="tab.key === ACTIVITY_TAB.key && activity"
            :entity-type="activity.entityType"
            :entity-id="activity.entityId"
          />
          <slot v-else :name="tab.key" />
        </template>
      </UiTabs>

      <template v-else>
        <form :id="formId" class="space-y-4" novalidate @submit.prevent="emit('submit')">
          <UiAlert v-if="formError" :message="formError" />
          <slot />
        </form>
        <slot name="extra" />
      </template>
    </div>

    <template #footer="{ close }">
      <UiButton variant="secondary" :disabled="submitting" @click="close">
        {{ showSubmit ? cancelLabel : 'Cerrar' }}
      </UiButton>
      <UiButton v-if="showSubmit" type="submit" :form="formId" :loading="submitting">
        {{ submitLabel }}
      </UiButton>
    </template>
  </UiModal>
</template>
