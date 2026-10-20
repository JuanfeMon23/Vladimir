<script setup lang="ts">
import { z } from 'zod'
import type { LabAreaRead } from '../types/lab-areas'

/**
 * Crear (`entity = null`) o ver/editar un área en modal desde el listado. En
 * edición incluye el sub-recurso "encargado" (asignar + historial) en
 * `LabAreaManagerPanel`, fuera del `<form>` principal.
 */
const props = defineProps<{
  entity: LabAreaRead | null
}>()

const emit = defineEmits<{
  /** Se guardó algo (área o encargado): el listado debe recargarse. */
  saved: []
}>()

const open = defineModel<boolean>('open', { required: true })

const schema = z.object({
  code: zRequiredText('El código es obligatorio.', 64),
  name: zRequiredText('El nombre es obligatorio.', 100),
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

const labAreasApi = useLabAreas()

// Al ver/editar, cada grupo de campos exige su permiso (el backend también lo valida).
const canEdit = useCan(LAB_AREAS_TAGS.edit)
const canChangeStatus = useCan(LAB_AREAS_TAGS.changeStatus)
const readOnly = computed(() => isEdit.value && !canEdit.value && !canChangeStatus.value)

const onSubmit = submit(async (values) => {
  if (props.entity) {
    const body = buildLabAreaUpdate(values, props.entity, { canEdit: canEdit.value, canChangeStatus: canChangeStatus.value })
    if (!body) {
      open.value = false
      return
    }
    await labAreasApi.update(props.entity.id, body)
  } else {
    await labAreasApi.create(withActivityReason(values, undefined))
  }
  emit('saved')
  open.value = false
})
</script>

<template>
  <UiFormModal
    v-model:open="open"
    :activity="entity ? { entityType: 'lab_areas', entityId: entity.id } : null"
    :title="!isEdit ? 'Nueva área' : readOnly ? 'Área' : 'Editar área'"
    :size="isEdit ? 'xl' : 'md'"
    :submitting="isSubmitting"
    :form-error="formError"
    :submit-label="readOnly ? 'Cerrar' : isEdit ? 'Guardar cambios' : 'Crear'"
    @submit="onSubmit"
  >
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <UiFormField name="code" label="Código" required>
        <UiTextInput :disabled="isEdit && !canEdit" />
      </UiFormField>
      <UiFormField name="name" label="Nombre" required>
        <UiTextInput :disabled="isEdit && !canEdit" />
      </UiFormField>
      <UiFormField name="description" label="Descripción" class="sm:col-span-2">
        <UiTextarea :rows="3" :disabled="isEdit && !canEdit" />
      </UiFormField>
    </div>
    <UiActiveField v-if="!isEdit || canChangeStatus" label="Activa" :initial="entity?.is_active" />

    <template v-if="entity" #extra>
      <LabAreaManagerPanel :area-id="entity.id" :current-manager="entity.current_manager" @changed="emit('saved')" />
    </template>
  </UiFormModal>
</template>
