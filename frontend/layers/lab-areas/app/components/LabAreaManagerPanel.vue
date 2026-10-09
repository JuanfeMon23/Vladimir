<script setup lang="ts">
import { z } from 'zod'
import type { UiSelectOption } from '~/components/ui/UiSelect.vue'
import type { LabAreaStaffOption, ManagerAssignmentRead } from '../types/lab-areas'

/**
 * Sub-recurso "encargado" de un área, dentro del modal de edición: encargado
 * vigente, formulario para asignar uno nuevo (`PUT /lab-areas/{id}/manager`)
 * e historial (`GET /lab-areas/{id}/manager-history`). Tiene su propio
 * formulario zod, separado del de los datos del área.
 */
const props = defineProps<{
  areaId: string
  currentManager: ManagerAssignmentRead | null
}>()

const emit = defineEmits<{
  changed: []
}>()

const labAreasApi = useLabAreas()

const manager = ref<ManagerAssignmentRead | null>(props.currentManager)

const history = ref<ManagerAssignmentRead[]>([])
const historyLoading = ref(false)
const historyError = ref<string | null>(null)

const staffOptions = ref<UiSelectOption[]>([])
const staffLoading = ref(false)
const staffError = ref<string | null>(null)

const schema = z.object({
  staff_id: z.string({ required_error: 'Selecciona un miembro del personal.' }).min(1, 'Selecciona un miembro del personal.'),
  notes: zOptionalText()
})

const { submit, isSubmitting, formError, reset } = useZodForm(schema, {
  initialValues: { staff_id: '', notes: '' }
})

function toOption(person: LabAreaStaffOption): UiSelectOption {
  return { value: person.id, label: `${person.first_name} ${person.last_name}` }
}

async function fetchHistory() {
  historyLoading.value = true
  historyError.value = null
  try {
    history.value = await labAreasApi.managerHistory(props.areaId)
  } catch (err) {
    historyError.value = err instanceof Error ? err.message : 'No se pudo cargar el historial de encargados.'
  } finally {
    historyLoading.value = false
  }
}

async function fetchStaff() {
  staffLoading.value = true
  staffError.value = null
  try {
    const result = await labAreasApi.listEligibleManagers()
    staffOptions.value = result.items.map(toOption)
  } catch (err) {
    staffError.value = err instanceof Error ? err.message : 'No se pudo cargar el personal activo.'
  } finally {
    staffLoading.value = false
  }
}

const onAssign = submit(async (values) => {
  manager.value = await labAreasApi.assignManager(props.areaId, values)
  reset()
  emit('changed')
  await fetchHistory()
})

function formatDate(value: string | null) {
  if (!value) return 'Vigente'
  return new Date(value).toLocaleDateString('es', { year: 'numeric', month: 'short', day: 'numeric' })
}

onMounted(() => {
  fetchHistory()
  fetchStaff()
})
</script>

<template>
  <div class="space-y-6">
    <UiSection title="Encargado" divided>
      <template #aside>
        <p class="text-sm text-text-muted">
          Vigente:
          <span class="font-medium text-text">{{ manager ? manager.staff_name : 'Sin encargado' }}</span>
        </p>
      </template>

      <UiAlert v-if="staffError" :message="staffError" />

      <form class="space-y-3" novalidate @submit.prevent="onAssign">
        <UiAlert v-if="formError" :message="formError" />
        <div class="grid grid-cols-1 items-start gap-3 sm:grid-cols-[1fr_1fr_auto]">
          <UiFormField name="staff_id" label="Nuevo encargado" required>
            <UiSelect
              :options="staffOptions"
              :placeholder="staffLoading ? 'Cargando personal…' : 'Seleccionar personal activo'"
              :disabled="staffLoading"
            />
          </UiFormField>
          <UiFormField name="notes" label="Notas">
            <UiTextInput />
          </UiFormField>
          <UiButton type="submit" class="sm:mt-6.5" :loading="isSubmitting">
            Asignar
          </UiButton>
        </div>
      </form>
    </UiSection>

    <UiSection title="Historial de encargados">
      <UiAlert v-if="historyError" :message="historyError" />
      <UiItemList
        v-else
        :items="history"
        :row-key="(a: ManagerAssignmentRead) => a.id"
        :loading="historyLoading"
        empty-message="Sin historial de encargados."
      >
        <template #default="{ item }">
          <p class="font-medium text-text">
            {{ item.staff_name }}
          </p>
          <p v-if="item.notes" class="text-text-muted">
            {{ item.notes }}
          </p>
        </template>
        <template #trailing="{ item }">
          <span class="text-text-muted">{{ formatDate(item.start_at) }} — {{ formatDate(item.end_at) }}</span>
          <UiStatusBadge v-if="!item.end_at" variant="success" label="Vigente" />
        </template>
      </UiItemList>
    </UiSection>
  </div>
</template>
