<script setup lang="ts">
import { z } from 'zod'
import type { UiVersionSectionApi } from '~/components/ui/UiVersionSection.vue'
import { PRINT_LABEL_FIRST_VERSION_DEFAULTS } from '../types/print-labels'
import type { PrintLabelRead } from '../types/print-labels'

/**
 * Crear o ver/editar una etiqueta de impresión, en modal desde el listado.
 * Al editar, el `#extra` muestra sus versiones (`UiVersionSection`): crear un
 * borrador abre el editor de versión (página propia).
 */
const props = defineProps<{ entity: PrintLabelRead | null }>()
const emit = defineEmits<{ saved: [] }>()
const open = defineModel<boolean>('open', { required: true })

const schema = z.object({
  code: zRequiredText('El código es obligatorio.', 64),
  name: zRequiredText('El nombre es obligatorio.', 150),
  description: zOptionalText(),
  is_active: z.boolean(),
  activity_reason: zActivityReason()
})

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

const printLabelsApi = usePrintLabels()

const onSubmit = submit(async (values) => {
  if (props.entity) await printLabelsApi.update(props.entity.id, withActivityReason(values, props.entity.is_active))
  else await printLabelsApi.create(withActivityReason(values, undefined))
  emit('saved')
  open.value = false
})

const versionsApi = computed<UiVersionSectionApi | null>(() => {
  const id = props.entity?.id
  if (!id) return null
  return {
    list: async () => (await printLabelsApi.listVersions(id, { page_size: 100 })).items,
    create: isFirst => printLabelsApi.createVersion(id, isFirst ? { ...PRINT_LABEL_FIRST_VERSION_DEFAULTS } : {}),
    publish: versionId => printLabelsApi.publishVersion(id, versionId),
    retire: versionId => printLabelsApi.retireVersion(id, versionId),
    editorPath: versionId => `/print-labels/${id}/versions/${versionId}`
  }
})
</script>

<template>
  <UiFormModal
    v-model:open="open"
    :activity="entity ? { entityType: 'print_labels', entityId: entity.id } : null"
    :title="entity ? 'Editar etiqueta' : 'Nueva etiqueta'"
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
      <UiFormField name="description" label="Descripción" class="sm:col-span-2">
        <UiTextarea :rows="2" />
      </UiFormField>
    </div>
    <UiActiveField label="Activa" :initial="entity?.is_active" />

    <template v-if="versionsApi" #extra>
      <UiVersionSection :api="versionsApi" />
    </template>
  </UiFormModal>
</template>
