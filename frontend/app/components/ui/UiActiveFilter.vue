<script setup lang="ts">
/**
 * Filtro "Estado" (activo/inactivo/todos) para listados de módulo.
 * Envuelve `UiSelect`: traduce el valor tri-estado del control a
 * `boolean | undefined` (`undefined` = todos), que es lo que esperan
 * los composables de API (`list({ active })`).
 */
import UiSelect from './UiSelect.vue'

type ActiveFilterValue = 'all' | 'active' | 'inactive'

const props = withDefaults(
  defineProps<{
    modelValue: boolean | undefined
    id?: string
    label?: string
    allLabel?: string
    activeLabel?: string
    inactiveLabel?: string
  }>(),
  {
    id: 'ui-active-filter',
    label: 'Estado',
    allLabel: 'Todos',
    activeLabel: 'Activos',
    inactiveLabel: 'Inactivos'
  }
)

const emit = defineEmits<{
  'update:modelValue': [value: boolean | undefined]
}>()

const options = computed(() => [
  { value: 'all', label: props.allLabel },
  { value: 'active', label: props.activeLabel },
  { value: 'inactive', label: props.inactiveLabel }
])

const selectValue = computed<ActiveFilterValue>(() => {
  if (props.modelValue === undefined) return 'all'
  return props.modelValue ? 'active' : 'inactive'
})

function onSelect(value: string) {
  const next = value as ActiveFilterValue
  emit('update:modelValue', next === 'all' ? undefined : next === 'active')
}
</script>

<template>
  <div class="flex items-center gap-2">
    <label :for="id" class="text-sm font-medium text-text-muted">
      {{ label }}
    </label>
    <UiSelect
      :id="id"
      class="min-w-36"
      variant="bordered"
      :model-value="selectValue"
      :options="options"
      @update:model-value="onSelect"
    />
  </div>
</template>
