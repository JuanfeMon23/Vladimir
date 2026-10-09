<script setup lang="ts">
import { z } from 'zod'
import type { ResultTemplateSectionRead } from '../types/result-templates'

/** Crear o editar una sección de una versión de plantilla (solo en borrador). */
const props = defineProps<{
  entity: ResultTemplateSectionRead | null
  templateId: string
  versionId: string
  nextSortOrder?: number
}>()
const emit = defineEmits<{ saved: [] }>()
const open = defineModel<boolean>('open', { required: true })

const schema = z.object({
  name: zRequiredText('El nombre es obligatorio.', 150),
  sort_order: zRequiredNumber('El orden es obligatorio.', { min: 0, integer: true })
})

const { submit, isSubmitting, formError } = useZodForm(schema, {
  initialValues: () => ({
    name: props.entity?.name ?? '',
    sort_order: props.entity?.sort_order ?? props.nextSortOrder ?? 0
  }),
  resetOn: open
})

const onSubmit = submit(async (values) => {
  const api = useResultTemplates()
  if (props.entity) await api.updateSection(props.templateId, props.versionId, props.entity.id, values)
  else await api.createSection(props.templateId, props.versionId, values)
  emit('saved')
  open.value = false
})
</script>

<template>
  <UiFormModal
    v-model:open="open"
    :activity="entity ? { entityType: 'result_template_sections', entityId: entity.id } : null"
    :title="entity ? 'Editar sección' : 'Nueva sección'"
    :submitting="isSubmitting"
    :form-error="formError"
    :submit-label="entity ? 'Guardar cambios' : 'Agregar'"
    @submit="onSubmit"
  >
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-[1fr_8rem]">
      <UiFormField name="name" label="Nombre" required>
        <UiTextInput />
      </UiFormField>
      <UiFormField name="sort_order" label="Orden" required>
        <UiTextInput type="number" step="1" min="0" />
      </UiFormField>
    </div>
  </UiFormModal>
</template>
