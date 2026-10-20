<script setup lang="ts">
import { z } from 'zod'
import {
  PRECONDITION_CATEGORIES,
  PRECONDITION_CATEGORY_LABELS,
  PRECONDITION_DURATION_UNITS,
  PRECONDITION_DURATION_UNIT_LABELS
} from '../types/preconditions'
import type { PreconditionRead } from '../types/preconditions'

/**
 * Crear o ver/editar una precondición raíz o un ítem, en modal (el contrato
 * usa el mismo body para ambos):
 * - `entity = null`, `parent = null` → nueva precondición raíz.
 * - `entity = null`, `parent = raíz` → nuevo ítem de esa raíz.
 * - `entity` raíz → editar + sub-recurso "ítems" (lista, agregar, editar en
 *   un modal anidado de este mismo componente).
 * - `entity` ítem → editar el ítem.
 */
const props = withDefaults(
  defineProps<{
    entity: PreconditionRead | null
    parent?: PreconditionRead | null
  }>(),
  { parent: null }
)

const emit = defineEmits<{
  /** Se guardó algo (precondición o ítems): el listado debe recargarse. */
  saved: []
}>()

const open = defineModel<boolean>('open', { required: true })

const schema = z.object({
  code: zRequiredText('El código es obligatorio.', 64),
  name: zRequiredText('El nombre es obligatorio.', 150),
  category: zRequiredEnum(PRECONDITION_CATEGORIES, 'Selecciona una categoría.'),
  duration_value: zOptionalNumber({ min: 0 }),
  duration_unit: zOptionalEnum(PRECONDITION_DURATION_UNITS),
  description: zOptionalText(),
  patient_instructions: zOptionalText(),
  is_active: z.boolean(),
  activity_reason: zActivityReason()
})

const categoryOptions = toSelectOptions(PRECONDITION_CATEGORY_LABELS)
const durationUnitOptions = toSelectOptions(PRECONDITION_DURATION_UNIT_LABELS)

const isEdit = computed(() => props.entity !== null)
const isItem = computed(() => (props.entity ? props.entity.kind === 'condition' : props.parent !== null))
const isRootEdit = computed(() => props.entity?.kind === 'precondition')

const title = computed(() => {
  if (isItem.value) return !isEdit.value ? 'Nuevo ítem' : readOnly.value ? 'Ítem' : 'Editar ítem'
  return !isEdit.value ? 'Nueva precondición' : readOnly.value ? 'Precondición' : 'Editar precondición'
})
const description = computed(() => {
  if (props.parent && !isEdit.value) return `Ítem de «${props.parent.name}».`
  return undefined
})

const { submit, isSubmitting, formError } = useZodForm(schema, {
  initialValues: () => {
    const source = props.entity
    return {
      code: source?.code ?? '',
      name: source?.name ?? '',
      category: source?.category ?? props.parent?.category ?? '',
      duration_value: source?.duration_value ?? '',
      duration_unit: source?.duration_unit ?? '',
      description: source?.description ?? '',
      patient_instructions: source?.patient_instructions ?? '',
      is_active: source?.is_active ?? true,
      activity_reason: ''
    }
  },
  resetOn: open
})

const preconditionsApi = usePreconditions()

// Al ver/editar, cada grupo de campos exige su permiso (el backend también lo valida).
const canEdit = useCan(PRECONDITIONS_TAGS.edit)
const canChangeStatus = useCan(PRECONDITIONS_TAGS.changeStatus)
const readOnly = computed(() => isEdit.value && !canEdit.value && !canChangeStatus.value)
/** Los datos son de solo lectura al editar sin `edit`. */
const dataLocked = computed(() => isEdit.value && !canEdit.value)
const canModify = useCan([PRECONDITIONS_TAGS.edit, PRECONDITIONS_TAGS.changeStatus], 'any')

const onSubmit = submit(async (values) => {
  if (props.entity) {
    const body = buildGuardedUpdate(values, props.entity, { canEdit: canEdit.value, canChangeStatus: canChangeStatus.value })
    if (!body) {
      open.value = false
      return
    }
    await preconditionsApi.update(props.entity.id, body)
  } else if (props.parent) await preconditionsApi.createItem(props.parent.id, withActivityReason(values, undefined))
  else await preconditionsApi.create(withActivityReason(values, undefined))
  emit('saved')
  open.value = false
})

// --- Sub-recurso: ítems (solo al editar una raíz) ---
const itemList = useChildCollection<PreconditionRead>({
  open,
  initial: () => props.entity?.items ?? [],
  refetch: async () => (props.entity ? (await preconditionsApi.get(props.entity.id)).items ?? [] : []),
  errorMessage: 'No se pudieron recargar los ítems.'
})

function onItemSaved() {
  emit('saved')
  itemList.refresh()
}
</script>

<template>
  <UiFormModal
    v-model:open="open"
    :activity="entity ? { entityType: 'preconditions', entityId: entity.id } : null"
    :title="title"
    :description="description"
    :size="isRootEdit ? 'xl' : 'lg'"
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
      <UiFormField name="category" label="Categoría" required>
        <UiSelect :options="categoryOptions" placeholder="Seleccionar categoría" :disabled="dataLocked" />
      </UiFormField>
      <div class="grid grid-cols-2 gap-3">
        <UiFormField name="duration_value" label="Duración">
          <UiTextInput type="number" min="0" step="any" :disabled="dataLocked" />
        </UiFormField>
        <UiFormField name="duration_unit" label="Unidad">
          <UiSelect :options="durationUnitOptions" empty-label="Sin unidad" :disabled="dataLocked" />
        </UiFormField>
      </div>
      <UiFormField name="description" label="Descripción" class="sm:col-span-2">
        <UiTextarea :rows="2" :disabled="dataLocked" />
      </UiFormField>
      <UiFormField
        name="patient_instructions"
        label="Instrucciones al paciente"
        class="sm:col-span-2"
        hint="Texto que verá el paciente al preparar el examen."
      >
        <UiTextarea :rows="3" :disabled="dataLocked" />
      </UiFormField>
    </div>
    <UiActiveField v-if="!isEdit || canChangeStatus" label="Activa" :initial="entity?.is_active" />

    <template v-if="isRootEdit && entity" #extra>
      <UiSection title="Ítems" description="Condiciones específicas de esta precondición." divided>
        <template #actions>
          <LeoCan :tag="PRECONDITIONS_TAGS.addItem">
            <UiButton
              variant="secondary"
              size="sm"
              :disabled="!entity.is_active"
              :title="entity.is_active ? undefined : 'Reactiva la precondición para agregarle ítems.'"
              @click="itemList.modal.openCreate()"
            >
              Agregar ítem
            </UiButton>
          </LeoCan>
        </template>

        <UiAlert v-if="itemList.error" :message="itemList.error" />
        <UiItemList
          :items="itemList.items"
          :row-key="(item: PreconditionRead) => item.id"
          :loading="itemList.loading"
          :inactive="(item: PreconditionRead) => !item.is_active"
          empty-message="Sin ítems."
        >
          <template #default="{ item }">
            <span class="text-text">{{ item.name }}</span>
            <span class="text-text-muted"> ({{ item.code }})</span>
          </template>
          <template #trailing="{ item }">
            <UiStatusBadge :active="item.is_active" />
            <UiButton variant="ghost" size="sm" @click="itemList.modal.openEdit(item)">
              {{ canModify ? 'Editar' : 'Ver' }}
            </UiButton>
          </template>
        </UiItemList>
      </UiSection>

      <PreconditionFormModal
        v-model:open="itemList.modal.open"
        :entity="itemList.modal.entity"
        :parent="entity"
        @saved="onItemSaved"
      />
    </template>
  </UiFormModal>
</template>
