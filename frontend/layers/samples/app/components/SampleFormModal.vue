<script setup lang="ts">
import { z } from 'zod'
import type { SampleRead, SampleTypeRead } from '../types/samples'

/**
 * Crear (`entity = null`) o ver/editar una muestra en modal desde el listado.
 * En edición incluye el sub-recurso "tipos de muestra" (lista, agregar y
 * editar en `SampleTypeFormModal` anidado), fuera del `<form>` principal.
 */
const props = defineProps<{
  entity: SampleRead | null
}>()

const emit = defineEmits<{
  /** Se guardó algo (muestra o tipos): el listado debe recargarse. */
  saved: []
}>()

const open = defineModel<boolean>('open', { required: true })

const schema = z.object({
  code: zRequiredText('El código es obligatorio.', 64),
  name: zRequiredText('El nombre es obligatorio.', 150),
  description: zOptionalText(),
  is_active: z.boolean(),
  activity_reason: zActivityReason()
})

const isEdit = computed(() => props.entity !== null)

const { submit, isSubmitting, formError } = useZodForm(schema, {
  initialValues: () => ({
    code: props.entity?.code ?? '',
    name: props.entity?.name ?? '',
    description: props.entity?.description ?? '',
    is_active: props.entity?.is_active ?? true,
    activity_reason: ''
  }),
  resetOn: open
})

const samplesApi = useSamples()

// Al ver/editar, cada grupo de campos exige su permiso (el backend también lo valida).
const canEdit = useCan(SAMPLES_TAGS.edit)
const canChangeStatus = useCan(SAMPLES_TAGS.changeStatus)
const readOnly = computed(() => isEdit.value && !canEdit.value && !canChangeStatus.value)
/** Los datos son de solo lectura al editar sin `edit`. */
const dataLocked = computed(() => isEdit.value && !canEdit.value)
const canModify = useCan([SAMPLES_TAGS.edit, SAMPLES_TAGS.changeStatus], 'any')

const onSubmit = submit(async (values) => {
  if (props.entity) {
    const body = buildGuardedUpdate(values, props.entity, { canEdit: canEdit.value, canChangeStatus: canChangeStatus.value })
    if (!body) {
      open.value = false
      return
    }
    await samplesApi.update(props.entity.id, body)
  } else await samplesApi.create(withActivityReason(values, undefined))
  emit('saved')
  open.value = false
})

// --- Sub-recurso: tipos de muestra (solo en edición) ---
const types = useChildCollection<SampleTypeRead>({
  open,
  initial: () => props.entity?.types ?? [],
  refetch: async () => (props.entity ? (await samplesApi.get(props.entity.id)).types : []),
  errorMessage: 'No se pudieron recargar los tipos.'
})

function onTypeSaved() {
  emit('saved')
  types.refresh()
}
</script>

<template>
  <UiFormModal
    v-model:open="open"
    :activity="entity ? { entityType: 'samples', entityId: entity.id } : null"
    :title="!isEdit ? 'Nueva muestra' : readOnly ? 'Muestra' : 'Editar muestra'"
    :size="isEdit ? 'xl' : 'md'"
    :submitting="isSubmitting"
    :form-error="formError"
    :submit-label="readOnly ? 'Cerrar' : isEdit ? 'Guardar cambios' : 'Crear'"
    @submit="onSubmit"
  >
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <UiFormField name="code" label="Código" required>
        <UiTextInput :disabled="dataLocked" />
      </UiFormField>
      <UiFormField name="name" label="Nombre" required>
        <UiTextInput :disabled="dataLocked" />
      </UiFormField>
      <UiFormField name="description" label="Descripción" class="sm:col-span-2">
        <UiTextarea :rows="2" :disabled="dataLocked" />
      </UiFormField>
    </div>
    <UiActiveField v-if="!isEdit || canChangeStatus" label="Activa" :initial="entity?.is_active" />

    <template v-if="entity" #extra>
      <UiSection title="Tipos de muestra" description="Tubo/tapa, aditivo, volumen y conservación." divided>
        <template #actions>
          <LeoCan :tag="SAMPLES_TAGS.addType">
            <UiButton
              variant="secondary"
              size="sm"
              :disabled="!entity.is_active"
              :title="entity.is_active ? undefined : 'Reactiva la muestra para agregarle tipos.'"
              @click="types.modal.openCreate()"
            >
              Agregar tipo
            </UiButton>
          </LeoCan>
        </template>

        <UiAlert v-if="types.error" :message="types.error" />
        <UiItemList
          :items="types.items"
          :row-key="(type: SampleTypeRead) => type.id"
          :loading="types.loading"
          :inactive="(type: SampleTypeRead) => !type.is_active"
          empty-message="Sin tipos."
        >
          <template #default="{ item }">
            <SampleTypeCapChip :label="`${item.name} (${item.code})`" :cap-color-hex="item.cap_color_hex" />
          </template>
          <template #trailing="{ item }">
            <UiStatusBadge :active="item.is_active" />
            <UiButton variant="ghost" size="sm" @click="types.modal.openEdit(item)">
              {{ canModify ? 'Editar' : 'Ver' }}
            </UiButton>
          </template>
        </UiItemList>
      </UiSection>

      <SampleTypeFormModal
        v-model:open="types.modal.open"
        :sample-id="entity.id"
        :entity="types.modal.entity"
        @saved="onTypeSaved"
      />
    </template>
  </UiFormModal>
</template>
