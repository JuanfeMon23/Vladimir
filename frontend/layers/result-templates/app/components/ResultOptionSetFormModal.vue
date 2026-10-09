<script setup lang="ts">
import { z } from 'zod'
import type { ResultOptionRead, ResultOptionSetRead } from '../types/result-templates'

/**
 * Crear o ver/editar un conjunto de opciones, en modal desde el listado. Al
 * editar, el `#extra` lista sus opciones; cada opción se crea/edita en un
 * modal anidado (`ResultOptionFormModal`), como los ítems de precondiciones.
 */
const props = defineProps<{ entity: ResultOptionSetRead | null }>()
const emit = defineEmits<{ saved: [] }>()
const open = defineModel<boolean>('open', { required: true })

const schema = z.object({
  code: zRequiredText('El código es obligatorio.', 64),
  name: zRequiredText('El nombre es obligatorio.', 150),
  is_active: z.boolean(),
  activity_reason: zActivityReason()
})

const { submit, isSubmitting, formError } = useZodForm(schema, {
  initialValues: () => ({
    code: props.entity?.code ?? '',
    name: props.entity?.name ?? '',
    is_active: props.entity?.is_active ?? true,
    activity_reason: ''
  }),
  resetOn: open
})

const optionSetsApi = useResultOptionSets()

const onSubmit = submit(async (values) => {
  if (props.entity) await optionSetsApi.update(props.entity.id, withActivityReason(values, props.entity.is_active))
  else await optionSetsApi.create(withActivityReason(values, undefined))
  emit('saved')
  open.value = false
})

// --- Sub-recurso: opciones (solo al editar) ---
const options = useChildCollection<ResultOptionRead>({
  open,
  initial: () => [],
  refetch: async () => {
    if (!props.entity) return []
    const page = await optionSetsApi.listOptions(props.entity.id, { page_size: 200 })
    return [...page.items].sort((a, b) => a.sort_order - b.sort_order)
  },
  errorMessage: 'No se pudieron cargar las opciones.'
})

// El listado de conjuntos no trae las opciones: se piden al abrir.
watch(open, (isOpen) => {
  if (isOpen && props.entity) options.refresh()
}, { immediate: true })

const nextSortOrder = computed(() =>
  options.items.reduce((max, option) => Math.max(max, option.sort_order + 1), 0)
)
</script>

<template>
  <UiFormModal
    v-model:open="open"
    :activity="entity ? { entityType: 'result_option_sets', entityId: entity.id } : null"
    :title="entity ? 'Editar conjunto de opciones' : 'Nuevo conjunto de opciones'"
    :size="entity ? 'lg' : 'md'"
    :submitting="isSubmitting"
    :form-error="formError"
    :submit-label="entity ? 'Guardar cambios' : 'Crear'"
    @submit="onSubmit"
  >
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <UiFormField name="code" label="Código" required>
        <UiTextInput />
      </UiFormField>
      <UiFormField name="name" label="Nombre" required>
        <UiTextInput />
      </UiFormField>
    </div>
    <UiActiveField label="Activo" :initial="entity?.is_active" />

    <template v-if="entity" #extra>
      <UiSection title="Opciones" description="Valores posibles del resultado, en orden." divided>
        <template #actions>
          <UiButton
            variant="secondary"
            size="sm"
            :disabled="!entity.is_active"
            :title="entity.is_active ? undefined : 'Reactiva el conjunto para agregarle opciones.'"
            @click="options.modal.openCreate()"
          >
            Agregar opción
          </UiButton>
        </template>

        <UiAlert v-if="options.error" :message="options.error" />
        <UiItemList
          :items="options.items"
          :row-key="(option: ResultOptionRead) => option.id"
          :loading="options.loading"
          :inactive="(option: ResultOptionRead) => !option.is_active"
          empty-message="Sin opciones todavía."
        >
          <template #default="{ item }">
            <span class="text-text">{{ item.label }}</span>
            <span class="text-text-muted"> ({{ item.code }} · orden {{ item.sort_order }})</span>
          </template>
          <template #trailing="{ item }">
            <UiStatusBadge v-if="item.is_abnormal" variant="warning" label="Anormal" />
            <UiStatusBadge :active="item.is_active" :label="item.is_active ? 'Activa' : 'Inactiva'" />
            <UiButton variant="ghost" size="sm" @click="options.modal.openEdit(item)">
              Editar
            </UiButton>
          </template>
        </UiItemList>
      </UiSection>

      <ResultOptionFormModal
        v-model:open="options.modal.open"
        :entity="options.modal.entity"
        :option-set="entity"
        :next-sort-order="nextSortOrder"
        @saved="options.refresh()"
      />
    </template>
  </UiFormModal>
</template>
