<script setup lang="ts">
import { z } from 'zod'
import type { UiVersionSectionApi } from '~/components/ui/UiVersionSection.vue'
import type { ResultTemplateRead } from '../types/result-templates'

/**
 * Crear o ver/editar una plantilla de resultados, en modal desde el listado.
 * Al editar, el `#extra` muestra sus versiones (`UiVersionSection`); las
 * secciones, analitos y rangos se editan en el editor de versión (página
 * propia).
 */
const props = defineProps<{ entity: ResultTemplateRead | null }>()
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

const resultTemplatesApi = useResultTemplates()

const onSubmit = submit(async (values) => {
  if (props.entity) await resultTemplatesApi.update(props.entity.id, withActivityReason(values, props.entity.is_active))
  else await resultTemplatesApi.create(withActivityReason(values, undefined))
  emit('saved')
  open.value = false
})

const versionsApi = computed<UiVersionSectionApi | null>(() => {
  const id = props.entity?.id
  if (!id) return null
  return {
    list: async () => (await resultTemplatesApi.listVersions(id, { page_size: 100 })).items,
    // `report_settings: {}` cubre la primera versión (obligatorio) y es un override vacío al clonar.
    create: () => resultTemplatesApi.createVersion(id),
    publish: versionId => resultTemplatesApi.publishVersion(id, versionId),
    retire: versionId => resultTemplatesApi.retireVersion(id, versionId),
    editorPath: versionId => `/result-templates/${id}/versions/${versionId}`
  }
})
</script>

<template>
  <UiFormModal
    v-model:open="open"
    :activity="entity ? { entityType: 'result_templates', entityId: entity.id } : null"
    :title="entity ? 'Editar plantilla' : 'Nueva plantilla'"
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
      <UiVersionSection
        :api="versionsApi"
        description="Secciones, analitos y rangos se editan por versión; solo un borrador es editable."
      />
    </template>
  </UiFormModal>
</template>
