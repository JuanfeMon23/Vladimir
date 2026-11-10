<script setup lang="ts">
import { z } from 'zod'
import type { CatalogCreate, CatalogItem, CatalogSlug, CatalogUpdate } from '~/types/catalogs'
import { catalogDefinition, catalogEntityType } from '../utils/catalogDefinitions'
import type { CatalogExtraField } from '../utils/catalogDefinitions'

/**
 * Crear o ver/editar un valor de un catálogo de categoría, en modal desde la
 * pantalla de catálogos. Los campos de comportamiento salen de la definición
 * del catálogo (`catalogDefinition`); el padre monta el modal con `:key="slug"`
 * para que el schema se arme una vez por catálogo. El `code` se fija al crear
 * y no se edita (otras tablas lo referencian); nada se elimina, se desactiva.
 */
const props = defineProps<{
  slug: CatalogSlug
  entity: (CatalogItem & Record<string, unknown>) | null
  /** Orden sugerido al crear (siguiente al mayor existente). */
  nextSortOrder: number
}>()
const emit = defineEmits<{ saved: [] }>()
const open = defineModel<boolean>('open', { required: true })

const definition = catalogDefinition(props.slug)

function extraFieldSchema(field: CatalogExtraField) {
  if (field.kind === 'boolean') return z.boolean()
  return zRequiredNumber(`${field.label}: es obligatorio.`, { min: 0, integer: field.kind === 'integer' })
    .refine(value => value > 0, `${field.label}: debe ser mayor que 0.`)
}

const schema = z.object({
  code: zRequiredText('El código es obligatorio.', 64),
  name: zRequiredText('El nombre es obligatorio.', 150),
  sort_order: zRequiredNumber('El orden es obligatorio.', { min: 0, integer: true }),
  ...Object.fromEntries(definition.extraFields.map(field => [field.key, extraFieldSchema(field)])),
  is_active: z.boolean(),
  activity_reason: zActivityReason()
})

function extraInitialValue(field: CatalogExtraField) {
  const saved = props.entity?.[field.key]
  if (field.kind === 'boolean') return saved === true
  return typeof saved === 'number' ? saved : ''
}

const { submit, isSubmitting, formError, setFieldError } = useZodForm(schema, {
  initialValues: () => ({
    code: props.entity?.code ?? '',
    name: props.entity?.name ?? '',
    sort_order: props.entity?.sort_order ?? props.nextSortOrder,
    ...Object.fromEntries(definition.extraFields.map(field => [field.key, extraInitialValue(field)])),
    is_active: props.entity?.is_active ?? true,
    activity_reason: ''
  }),
  resetOn: open
})

// Los campos de comportamiento dependen del catálogo: el schema los arma en ejecución, sin rutas tipadas.
const setBehaviorFieldError = setFieldError as (field: string, message: string) => void
const catalogApi = useCatalogApi()
const canEdit = useCan(CATALOGS_TAGS.edit)
const canChangeStatus = useCan(CATALOGS_TAGS.changeStatus)
const isEdit = computed(() => props.entity !== null)
const readOnly = computed(() => isEdit.value && !canEdit.value && !canChangeStatus.value)
const dataLocked = computed(() => isEdit.value && !canEdit.value)

const onSubmit = submit(async (values) => {
  try {
    if (props.entity) {
      const { code: _code, ...data } = values
      const body = buildGuardedUpdate(data, props.entity, { canEdit: canEdit.value, canChangeStatus: canChangeStatus.value })
      if (!body) {
        open.value = false
        return
      }
      await catalogApi.update(props.slug, props.entity.id, body as CatalogUpdate)
    } else {
      await catalogApi.create(props.slug, withActivityReason(values, undefined) as CatalogCreate)
    }
  } catch (err) {
    // Segundo comodín: su `details` trae `code` (un campo del form) además de `id`; va a la casilla que lo causa.
    const details = err instanceof LeoApiError && err.status === 409 ? (err.details as { id?: unknown } | null) : null
    if (typeof details?.id !== 'string') throw err
    setBehaviorFieldError('is_wildcard', (err as Error).message)
    return
  }
  emit('saved')
  open.value = false
})
</script>

<template>
  <UiFormModal
    v-model:open="open"
    :activity="entity ? { entityType: catalogEntityType(slug), entityId: entity.id } : null"
    :title="!entity ? definition.newLabel : readOnly ? 'Valor del catálogo' : 'Editar valor del catálogo'"
    :description="definition.label"
    :submitting="isSubmitting"
    :form-error="formError"
    :submit-label="readOnly ? 'Cerrar' : entity ? 'Guardar cambios' : 'Crear'"
    @submit="onSubmit"
  >
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <UiFormField
        name="code"
        label="Código"
        required
        :hint="isEdit ? 'El código no se edita: otras tablas lo referencian.' : 'Se fija al crear y no se podrá editar.'"
      >
        <UiTextInput :disabled="isEdit" />
      </UiFormField>
      <UiFormField name="name" label="Nombre" required>
        <UiTextInput :disabled="dataLocked" />
      </UiFormField>
      <UiFormField name="sort_order" label="Orden" required>
        <UiTextInput type="number" step="1" min="0" :disabled="dataLocked" />
      </UiFormField>
      <template v-for="field in definition.extraFields" :key="field.key">
        <UiFormField v-if="field.kind !== 'boolean'" :name="field.key" :label="field.label" :hint="field.hint" required>
          <UiTextInput type="number" min="0" :step="field.kind === 'integer' ? '1' : 'any'" :disabled="dataLocked" />
        </UiFormField>
        <UiFormField v-else :name="field.key" :hint="field.hint" class="sm:col-span-2">
          <UiCheckbox :label="field.label" :disabled="dataLocked" />
        </UiFormField>
      </template>
    </div>
    <UiActiveField v-if="!isEdit || canChangeStatus" label="Activo" :initial="entity?.is_active" />
  </UiFormModal>
</template>
