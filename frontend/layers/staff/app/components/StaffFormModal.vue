<script setup lang="ts">
import { z } from 'zod'
import type { StaffRead } from '../types/staff'

/**
 * Crear (`entity = null`) o ver/editar un miembro del personal, en modal desde
 * el listado. Límites de longitud según el contrato del backend.
 */
const props = defineProps<{
  entity: StaffRead | null
}>()

const emit = defineEmits<{
  /** Se guardó algo: el listado debe recargarse. */
  saved: []
}>()

const open = defineModel<boolean>('open', { required: true })

const schema = z.object({
  document_type: zRequiredText('El tipo de documento es obligatorio.', 32),
  document_number: zRequiredText('El número de documento es obligatorio.', 32),
  first_name: zRequiredText('Los nombres son obligatorios.', 100),
  last_name: zRequiredText('Los apellidos son obligatorios.', 100),
  email: zOptionalEmail(255),
  phone: zOptionalText(32),
  job_title: zOptionalText(100),
  professional_license: zOptionalText(64),
  is_active: z.boolean(),
  activity_reason: zActivityReason()
})

const isEdit = computed(() => props.entity !== null)

const { submit, isSubmitting, formError } = useZodForm(schema, {
  initialValues: () => ({
    document_type: props.entity?.document_type ?? '',
    document_number: props.entity?.document_number ?? '',
    first_name: props.entity?.first_name ?? '',
    last_name: props.entity?.last_name ?? '',
    email: props.entity?.email ?? '',
    phone: props.entity?.phone ?? '',
    job_title: props.entity?.job_title ?? '',
    professional_license: props.entity?.professional_license ?? '',
    is_active: props.entity?.is_active ?? true,
    activity_reason: ''
  }),
  resetOn: open
})

const staffApi = useStaff()

// Al ver/editar, cada grupo de campos exige su permiso (el backend también lo valida).
const canEdit = useCan(STAFF_TAGS.edit)
const canChangeStatus = useCan(STAFF_TAGS.changeStatus)
const readOnly = computed(() => isEdit.value && !canEdit.value && !canChangeStatus.value)
/** Los datos son de solo lectura al editar sin `edit`. */
const dataLocked = computed(() => isEdit.value && !canEdit.value)

const onSubmit = submit(async (values) => {
  if (props.entity) {
    const body = buildGuardedUpdate(values, props.entity, { canEdit: canEdit.value, canChangeStatus: canChangeStatus.value })
    if (!body) {
      open.value = false
      return
    }
    await staffApi.update(props.entity.id, body)
  } else {
    await staffApi.create(withActivityReason(values, undefined))
  }
  emit('saved')
  open.value = false
})
</script>

<template>
  <UiFormModal
    v-model:open="open"
    :activity="entity ? { entityType: 'staff', entityId: entity.id } : null"
    :title="!isEdit ? 'Nuevo miembro del personal' : readOnly ? 'Miembro del personal' : 'Editar miembro del personal'"
    size="lg"
    :submitting="isSubmitting"
    :form-error="formError"
    :submit-label="readOnly ? 'Cerrar' : isEdit ? 'Guardar cambios' : 'Crear'"
    @submit="onSubmit"
  >
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <UiFormField name="document_type" label="Tipo de documento" required>
        <UiTextInput :disabled="dataLocked" />
      </UiFormField>
      <UiFormField name="document_number" label="Número de documento" required>
        <UiTextInput :disabled="dataLocked" />
      </UiFormField>
      <UiFormField name="first_name" label="Nombres" required>
        <UiTextInput :disabled="dataLocked" />
      </UiFormField>
      <UiFormField name="last_name" label="Apellidos" required>
        <UiTextInput :disabled="dataLocked" />
      </UiFormField>
      <UiFormField name="email" label="Correo electrónico">
        <UiTextInput type="email" :disabled="dataLocked" />
      </UiFormField>
      <UiFormField name="phone" label="Teléfono">
        <UiTextInput type="tel" :disabled="dataLocked" />
      </UiFormField>
      <UiFormField name="job_title" label="Cargo">
        <UiTextInput :disabled="dataLocked" />
      </UiFormField>
      <UiFormField name="professional_license" label="Licencia profesional">
        <UiTextInput :disabled="dataLocked" />
      </UiFormField>
    </div>
    <UiActiveField v-if="!isEdit || canChangeStatus" label="Activo" :initial="entity?.is_active" />
  </UiFormModal>
</template>
