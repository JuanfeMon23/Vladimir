<script setup lang="ts">
import { z } from 'zod'
import type { UiVersionSectionApi } from '~/components/ui/UiVersionSection.vue'
import {
  CONSENT_DOCUMENT_FIRST_VERSION_DEFAULTS,
  CONSENT_DOCUMENT_TYPES,
  CONSENT_DOCUMENT_TYPE_LABELS,
  CONSENT_GENERAL_HINT
} from '../types/consent-documents'
import type { ConsentDocumentRead, ConsentDocumentVersionRead } from '../types/consent-documents'
import { isGeneralConsent, isGeneralDocumentConflict } from '../utils/consentDocuments'

/**
 * Crear o ver/editar un documento a firmar, en modal desde el listado. Al
 * editar, el `#extra` muestra sus versiones (`UiVersionSection`); el
 * contenido y el PDF se editan en el editor de versión (página propia).
 *
 * Solo puede haber un consentimiento general (`tratamiento_datos`) activo: el
 * 409 del backend se muestra junto a "Tipo de documento" y "Activo".
 */
const props = defineProps<{ entity: ConsentDocumentRead | null }>()
const emit = defineEmits<{ saved: [] }>()
const open = defineModel<boolean>('open', { required: true })

const documentTypeOptions = toSelectOptions(CONSENT_DOCUMENT_TYPE_LABELS)

const schema = z.object({
  code: zRequiredText('El código es obligatorio.', 64),
  name: zRequiredText('El nombre es obligatorio.', 150),
  document_type: zRequiredEnum(CONSENT_DOCUMENT_TYPES, 'Selecciona un tipo de documento.'),
  description: zOptionalText(),
  is_active: z.boolean(),
  activity_reason: zActivityReason()
})

const { submit, isSubmitting, formError, setFieldError } = useZodForm(schema, {
  initialValues: () => ({
    code: props.entity?.code ?? '',
    name: props.entity?.name ?? '',
    document_type: props.entity?.document_type ?? '',
    description: props.entity?.description ?? '',
    is_active: props.entity?.is_active ?? true,
    activity_reason: ''
  }),
  resetOn: open
})

const consentDocumentsApi = useConsentDocuments()

const onSubmit = submit(async (values) => {
  try {
    if (props.entity) await consentDocumentsApi.update(props.entity.id, withActivityReason(values, props.entity.is_active))
    else await consentDocumentsApi.create(withActivityReason(values, undefined))
  } catch (err) {
    // Segundo general activo: su `details` trae `code` (un campo del form), así que
    // el mapeo genérico lo pondría bajo "Código"; aquí va a los campos que lo causan.
    if (!isGeneralDocumentConflict(err)) throw err
    const message = (err as Error).message
    setFieldError('document_type', message)
    setFieldError('is_active', message)
    return
  }
  emit('saved')
  open.value = false
})

const versionsApi = computed<UiVersionSectionApi | null>(() => {
  const id = props.entity?.id
  if (!id) return null
  return {
    list: async () => (await consentDocumentsApi.listVersions(id, { page_size: 100 })).items,
    create: isFirst => consentDocumentsApi.createVersion(id, isFirst ? { ...CONSENT_DOCUMENT_FIRST_VERSION_DEFAULTS } : {}),
    publish: versionId => consentDocumentsApi.publishVersion(id, versionId),
    retire: versionId => consentDocumentsApi.retireVersion(id, versionId),
    editorPath: versionId => `/consent-documents/${id}/versions/${versionId}`,
    badges: version => [(version as ConsentDocumentVersionRead).has_file
      ? { label: 'PDF adjunto', variant: 'success' }
      : { label: 'Sin archivo', variant: 'neutral' }],
    publishBlockedReason: version => (version as ConsentDocumentVersionRead).has_file ? null : 'Adjunta el PDF antes de publicar.'
  }
})
</script>

<template>
  <UiFormModal
    v-model:open="open"
    :activity="entity ? { entityType: 'consent_documents', entityId: entity.id } : null"
    :title="entity ? 'Editar documento' : 'Nuevo documento'"
    :size="entity ? 'lg' : 'md'"
    :submitting="isSubmitting"
    :form-error="formError"
    :submit-label="entity ? 'Guardar cambios' : 'Crear'"
    @submit="onSubmit"
  >
    <UiStatusBadge
      v-if="entity && entity.is_active && isGeneralConsent(entity)"
      variant="primary"
      label="Consentimiento general vigente"
      dot
    />
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <UiFormField name="code" label="Código" required>
        <UiTextInput />
      </UiFormField>
      <UiFormField name="name" label="Nombre" required>
        <UiTextInput />
      </UiFormField>
      <UiFormField name="document_type" label="Tipo de documento" required :hint="CONSENT_GENERAL_HINT" class="sm:col-span-2">
        <UiSelect :options="documentTypeOptions" placeholder="Seleccionar tipo" />
      </UiFormField>
      <UiFormField name="description" label="Descripción" class="sm:col-span-2">
        <UiTextarea :rows="2" />
      </UiFormField>
    </div>
    <UiActiveField label="Activo" :initial="entity?.is_active" />

    <template v-if="versionsApi" #extra>
      <UiVersionSection :api="versionsApi" />
    </template>
  </UiFormModal>
</template>
