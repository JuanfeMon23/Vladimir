<script setup lang="ts">
/**
 * Referencia viva del sistema de diseño (no aparece en el menú). Muestra
 * todos los componentes del núcleo y el patrón obligatorio de formularios
 * (zod + vee-validate + mapeo de errores del backend) dentro de `UiModal`.
 * `/_design?modal=open` abre el modal al cargar.
 */
import { z } from 'zod'
import type { ActivityEventRead } from '#andromeda/types/activity'
import type { UiDataTableColumn } from '#andromeda/components/ui/UiDataTable.vue'
import type { UiSelectOption } from '#andromeda/components/ui/UiSelect.vue'
import type { UiTab } from '#andromeda/components/ui/UiTabs.vue'
import type { UiVersionTimelineEntry } from '#andromeda/components/ui/UiVersionTimeline.vue'

definePageMeta({ layout: 'default' })
useHead({ title: 'Sistema de diseño · Vladimir' })

const route = useRoute()

// ── Botones ─────────────────────────────────────────────────────────────
const variants = ['primary', 'secondary', 'danger', 'ghost', 'danger-ghost'] as const
const sizes = ['sm', 'md', 'lg'] as const

// ── Controles sueltos (modo controlado) ─────────────────────────────────
const text = ref('Texto de ejemplo')
const bordered = ref('')
const longText = ref('')
const selectValue = ref<string | null>(null)
const checked = ref(true)
const activeFilter = ref<boolean | undefined>(true)
const demoSearch = ref('')

const areaOptions: UiSelectOption[] = [
  { value: 'hematology', label: 'Hematología' },
  { value: 'chemistry', label: 'Química clínica' },
  { value: 'microbiology', label: 'Microbiología' }
]

// ── Tabla ───────────────────────────────────────────────────────────────
interface DemoRow extends Record<string, unknown> {
  id: string
  code: string
  name: string
  is_active: boolean
}

const columns: UiDataTableColumn<DemoRow>[] = [
  { key: 'code', label: 'Código' },
  { key: 'name', label: 'Nombre' },
  { key: 'is_active', label: 'Estado' },
  { key: 'id', label: 'Acciones', class: 'text-right' }
]
// Reactivo: el ejemplo de desactivar/reactivar cambia `is_active` en sitio.
const rows = reactive<DemoRow[]>([
  { id: '1', code: 'HEM', name: 'Hematología', is_active: true },
  { id: '2', code: 'QCL', name: 'Química clínica', is_active: true },
  { id: '3', code: 'MIC', name: 'Microbiología', is_active: false }
])
const tableLoading = ref(false)
const page = ref(1)

// ── Lista expandible / versiones ────────────────────────────────────────
const expandableItems = [
  { id: 'a', name: 'Ayuno', children: ['8 horas', '12 horas'] },
  { id: 'b', name: 'Suspender medicación', children: ['Anticoagulantes'] }
]
const versions: UiVersionTimelineEntry[] = [
  { id: 'v3', versionNumber: 3, status: 'draft', changeNotes: 'Ajuste de márgenes.' },
  { id: 'v2', versionNumber: 2, status: 'published', publishedAt: '2026-09-20T10:00:00Z' },
  { id: 'v1', versionNumber: 1, status: 'retired', publishedAt: '2026-08-01T09:30:00Z' }
]

// ── Visor de PDF ────────────────────────────────────────────────────────
const pdfOpen = ref(false)
// PDF mínimo de una página en blanco (las referencias xref no se validan en el visor).
const DEMO_PDF = [
  '%PDF-1.4',
  '1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj',
  '2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj',
  '3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 200]>>endobj',
  'trailer<</Root 1 0 R>>',
  '%%EOF'
].join('\n')
async function loadDemoPdf() {
  return { base64: btoa(DEMO_PDF), content_type: 'application/pdf' }
}

// ── Formulario con zod + vee-validate (patrón obligatorio) ──────────────
const demoSchema = z.object({
  code: z.string().trim().min(1, 'El código es obligatorio.').max(10, 'Máximo 10 caracteres.'),
  name: z.string().trim().min(1, 'El nombre es obligatorio.'),
  email: z.union([z.literal(''), z.string().trim().email('Correo electrónico inválido.')]),
  area: z.string().min(1, 'Selecciona un área.'),
  capacity: z.coerce.number({ invalid_type_error: 'Debe ser un número.' }).int('Debe ser un entero.').min(1, 'Mínimo 1.'),
  notes: z.string().max(200, 'Máximo 200 caracteres.'),
  is_active: z.boolean(),
  activity_reason: zActivityReason(),
  confirmed: z.literal(true, { errorMap: () => ({ message: 'Debes confirmar los datos.' }) })
})

type BackendSimulation = 'none' | 'conflict' | 'schema' | 'generic'
const simulation = ref<BackendSimulation>('conflict')
const simulationOptions: UiSelectOption[] = [
  { value: 'none', label: 'Respuesta 201 (éxito)' },
  { value: 'conflict', label: '409 conflict con details.code' },
  { value: 'schema', label: '422 de schema FastAPI (loc → email)' },
  { value: 'generic', label: '409 sin campo (error general)' }
]

const { submit, isSubmitting, formError, resetForm } = useZodForm(demoSchema, {
  initialValues: {
    code: '',
    name: '',
    email: '',
    area: '',
    capacity: 1,
    notes: '',
    is_active: true,
    activity_reason: '',
    confirmed: false as unknown as true
  }
})

const saved = ref<string | null>(null)

// Simula la llamada al composable del módulo (`useLabAreas().create(...)`).
async function fakeCreate(values: z.output<typeof demoSchema>) {
  await new Promise(resolve => setTimeout(resolve, 700))
  switch (simulation.value) {
    case 'conflict':
      throw new LeoApiError(
        409, 'conflict', `Ya existe un área con el código '${values.code}'.`, { code: values.code }
      )
    case 'schema':
      throw new LeoApiError(
        422, 'validation_error', 'Algunos datos no son válidos. Revisa los campos marcados.',
        [{ field: 'email', message: 'value is not a valid email address' }]
      )
    case 'generic':
      throw new LeoApiError(409, 'conflict', 'El área está en uso y no puede modificarse.')
    default:
      return values
  }
}

const modalOpen = ref(route.query.modal === 'open')

const onSubmit = submit(async (values) => {
  await fakeCreate(values)
  saved.value = `Guardado: ${values.code} · ${values.name}`
  modalOpen.value = false
  resetForm()
})

// ── Activación: nada se elimina, se desactiva (con motivo opcional) ────
// En una layer, la acción es el PATCH: `api.update(row.id, change)`.
const toggle = useToggleActive(async (row: DemoRow, change) => {
  await new Promise(resolve => setTimeout(resolve, 600))
  row.is_active = change.is_active
  lastChange.value = `${row.name}: ${change.is_active ? 'reactivada' : 'desactivada'}${change.activity_reason ? ` — «${change.activity_reason}»` : ''}`
}, { mapError: leoErrorMessage })
const lastChange = ref<string | null>(null)

const demoActivity: ActivityEventRead[] = [
  { id: 'a3', entity_type: 'lab_areas', entity_id: '1', action: 'activated', reason: 'Se reabre el servicio.', occurred_at: '2026-10-02T14:30:00Z' },
  { id: 'a2', entity_type: 'lab_areas', entity_id: '1', action: 'deactivated', reason: null, occurred_at: '2026-09-15T09:05:00Z' },
  { id: 'a1', entity_type: 'lab_areas', entity_id: '1', action: 'activated', reason: null, occurred_at: '2026-09-01T08:00:00Z' }
]

// ── Pestañas ────────────────────────────────────────────────────────────
const demoTabs: UiTab[] = [
  { key: 'general', label: 'General' },
  { key: 'children', label: 'Hijos' },
  { key: 'history', label: 'Historial' },
  { key: 'disabled', label: 'Deshabilitada', disabled: true }
]
const activeTab = ref('general')
const underlinedTab = ref('general')
/** El modal de ejemplo con pestañas (detalle grande, p. ej. un examen). */
const tabbedModal = ref(false)
function openModal(tabbed: boolean) {
  tabbedModal.value = tabbed
  modalOpen.value = true
}
const optionalArea = ref('')
</script>

<template>
  <div class="space-y-8">
    <UiPageHeader
      title="Sistema de diseño"
      description="Referencia viva de los componentes del núcleo (lenguaje visual inspirado en HeroUI). La cabecera es UiPageHeader."
      action-label="Nuevo"
      @action="modalOpen = true"
    />

    <UiCard title="Botones" description="Variante por semántica de acción; tamaños sm/md/lg; loading, disabled, icono y enlace.">
      <div class="space-y-4">
        <div v-for="size in sizes" :key="size" class="flex flex-wrap items-center gap-3">
          <UiButton v-for="variant in variants" :key="variant" :variant="variant" :size="size">
            {{ variant }} {{ size }}
          </UiButton>
        </div>
        <div class="flex flex-wrap items-center gap-3">
          <UiButton loading>
            Guardando
          </UiButton>
          <UiButton variant="danger" loading>
            Eliminando
          </UiButton>
          <UiButton disabled>
            Deshabilitado
          </UiButton>
          <UiButton variant="secondary" to="/">
            Enlace (NuxtLink)
          </UiButton>
          <UiButton variant="ghost" icon-only aria-label="Editar">
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path d="m5.433 13.917 1.262-3.155A4 4 0 0 1 7.58 9.42l6.92-6.918a2.121 2.121 0 0 1 3 3l-6.92 6.918c-.383.383-.84.685-1.343.886l-3.154 1.262a.5.5 0 0 1-.65-.65Z" />
            </svg>
          </UiButton>
        </div>
      </div>
    </UiCard>

    <div class="grid grid-cols-1 items-start gap-6 lg:grid-cols-2">
      <UiCard title="Chips de estado" description="UiStatusBadge (flat, opcional dot).">
        <div class="flex flex-wrap gap-2">
          <UiStatusBadge active />
          <UiStatusBadge :active="false" />
          <UiStatusBadge variant="warning" label="Pendiente" dot />
          <UiStatusBadge variant="primary" label="En progreso" dot />
          <UiStatusBadge variant="success" label="Hecho" dot />
          <UiStatusBadge variant="neutral" label="Borrador" />
        </div>
        <div class="mt-3 flex flex-wrap gap-2">
          <UiVersionStatusBadge status="draft" />
          <UiVersionStatusBadge status="published" />
          <UiVersionStatusBadge status="retired" />
        </div>
      </UiCard>

      <UiCard title="Avisos y spinner" description="UiAlert y UiSpinner.">
        <div class="space-y-3">
          <UiAlert variant="danger" message="No se pudo cargar el listado." />
          <UiAlert variant="warning" title="Atención" message="La versión publicada está en uso." />
          <UiAlert variant="success" message="Cambios guardados." />
          <UiAlert variant="info" message="Las versiones retiradas no se pueden editar." />
          <div class="flex items-center gap-4">
            <UiSpinner size="sm" color="primary" />
            <UiSpinner color="primary" />
            <UiSpinner size="lg" color="primary" />
          </div>
        </div>
      </UiCard>
    </div>

    <UiCard title="Controles de formulario" description="Modo controlado (v-model). Variantes flat (por defecto) y bordered; estado inválido; deshabilitado.">
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <UiFormField label="Texto (flat)" hint="Ayuda bajo el campo.">
          <UiTextInput v-model="text" placeholder="Escribe algo" />
        </UiFormField>
        <UiFormField label="Texto (bordered)" required>
          <UiTextInput v-model="bordered" variant="bordered" placeholder="Bordered" />
        </UiFormField>
        <UiFormField label="Con error" error="Este campo es obligatorio.">
          <UiTextInput model-value="" placeholder="Inválido" />
        </UiFormField>
        <UiFormField label="Con error (bordered)" error="Formato inválido.">
          <UiTextInput model-value="abc" variant="bordered" />
        </UiFormField>
        <UiFormField label="Select">
          <UiSelect v-model="selectValue" :options="areaOptions" placeholder="Seleccionar área" />
        </UiFormField>
        <UiFormField label="Select opcional (empty-label)" hint="La opción vacía es seleccionable.">
          <UiSelect v-model="optionalArea" :options="areaOptions" empty-label="Sin área" />
        </UiFormField>
        <UiFormField label="Deshabilitado">
          <UiTextInput model-value="No editable" disabled />
        </UiFormField>
        <UiFormField label="Textarea" class="sm:col-span-2">
          <UiTextarea v-model="longText" placeholder="Notas…" />
        </UiFormField>
        <div class="flex flex-wrap items-center gap-6 sm:col-span-2">
          <UiCheckbox v-model="checked" label="Activo" />
          <UiCheckbox :model-value="false" label="Con descripción" description="Texto secundario." />
          <UiCheckbox :model-value="false" label="Inválido" invalid />
          <UiCheckbox :model-value="true" label="Deshabilitado" disabled />
          <UiActiveFilter v-model="activeFilter" id="design-active-filter" />
        </div>
      </div>
    </UiCard>

    <UiCard title="Buscador de listados" description="UiListToolbar (UiSearchInput + filtros): v-model confirmado con debounce de 300 ms, Enter y Escape; el estado vacío de una búsqueda es UiSearchEmpty (vía search-term en UiDataTable / UiExpandableList).">
      <div class="space-y-4">
        <UiListToolbar v-model:search="demoSearch" search-placeholder="Buscar por código o nombre…">
          <UiActiveFilter v-model="activeFilter" id="design-search-active-filter" />
        </UiListToolbar>
        <p class="text-sm text-text-muted">
          Término confirmado: <span class="font-medium text-text">{{ demoSearch || '(vacío)' }}</span>
        </p>
        <UiSearchEmpty v-if="demoSearch" :term="demoSearch" @clear="demoSearch = ''" />
      </div>
    </UiCard>

    <UiCard title="Pestañas" description="UiTabs: variantes solid (por defecto) y underlined; teclado ← → Home End; los paneles visitados conservan su estado.">
      <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <UiTabs v-model="activeTab" :tabs="demoTabs" aria-label="Ejemplo solid">
          <template #general>
            <p class="text-sm text-text-muted">Datos generales de la entidad.</p>
          </template>
          <template #children>
            <UiFormField label="Campo con estado" hint="Cambia de pestaña y vuelve: el texto se conserva.">
              <UiTextInput v-model="text" />
            </UiFormField>
          </template>
          <template #history>
            <p class="text-sm text-text-muted">Historial de cambios.</p>
          </template>
        </UiTabs>
        <UiTabs v-model="underlinedTab" :tabs="demoTabs" variant="underlined" aria-label="Ejemplo underlined">
          <template #general>
            <p class="text-sm text-text-muted">Variante subrayada.</p>
          </template>
          <template #children>
            <p class="text-sm text-text-muted">Segunda pestaña.</p>
          </template>
          <template #history>
            <p class="text-sm text-text-muted">Tercera pestaña.</p>
          </template>
        </UiTabs>
      </div>
    </UiCard>

    <UiCard title="Tabla" description="UiDataTable con slots de celda, carga y paginación." padding="none">
      <template #actions>
        <UiButton variant="secondary" size="sm" @click="tableLoading = !tableLoading">
          {{ tableLoading ? 'Ver filas' : 'Ver carga' }}
        </UiButton>
      </template>
      <div class="px-2 pb-2">
        <UiDataTable
          v-model:page="page"
          class="shadow-none!"
          :columns="columns"
          :rows="rows"
          :loading="tableLoading"
          :page-size="3"
          :total="9"
        >
          <template #cell-is_active="{ row }">
            <UiStatusBadge :active="row.is_active" />
          </template>
          <template #cell-id="{ row }">
            <div class="flex justify-end gap-1">
              <UiButton variant="ghost" size="sm" @click="modalOpen = true">
                Editar
              </UiButton>
              <UiButton :variant="row.is_active ? 'danger-ghost' : 'ghost'" size="sm" @click="toggle.ask(row)">
                {{ row.is_active ? 'Desactivar' : 'Reactivar' }}
              </UiButton>
            </div>
          </template>
        </UiDataTable>
      </div>
    </UiCard>

    <div class="grid grid-cols-1 items-start gap-6 lg:grid-cols-2">
      <section class="space-y-3">
        <h3 class="text-base font-semibold text-text">
          Lista expandible
        </h3>
        <UiExpandableList :items="expandableItems" :row-key="item => item.id">
          <template #header="{ item }">
            <span class="text-sm font-medium text-text">{{ item.name }}</span>
          </template>
          <template #summary="{ item }">
            <UiStatusBadge variant="neutral" :label="`${item.children.length} ${item.children.length === 1 ? 'ítem' : 'ítems'}`" />
          </template>
          <template #content="{ item }">
            <p v-for="child in item.children" :key="child" class="text-sm text-text-muted">
              {{ child }}
            </p>
          </template>
        </UiExpandableList>
      </section>

      <section class="space-y-3">
        <h3 class="text-base font-semibold text-text">
          Línea de tiempo de versiones
        </h3>
        <UiVersionTimeline :versions="versions">
          <template #actions="{ version }">
            <UiButton v-if="version.status === 'draft'" size="sm">
              Publicar
            </UiButton>
            <UiButton v-else-if="version.status === 'published'" size="sm" variant="secondary">
              Retirar
            </UiButton>
          </template>
        </UiVersionTimeline>
      </section>
    </div>

    <UiCard title="Visor de PDF" description="UiPdfPreviewModal: pide el archivo solo al abrir (load), lo muestra desde un Blob URL (revocado al cerrar) y ofrece Descargar. Aquí con un PDF mínimo generado en memoria.">
      <UiButton variant="secondary" @click="pdfOpen = true">
        Abrir visor de PDF
      </UiButton>
      <UiPdfPreviewModal v-model:open="pdfOpen" title="Consentimiento de ejemplo" filename="EJEMPLO-v1.pdf" :load="loadDemoPdf" :map-error="leoErrorMessage" />
    </UiCard>

    <UiCard title="Formulario en modal (zod + vee-validate)" description="Patrón obligatorio: crear/editar desde el listado en UiFormModal (UiModal + form + UiAlert + Cancelar/Guardar). Elige qué responde el backend simulado.">
      <div class="flex flex-wrap items-end gap-4">
        <UiFormField label="Respuesta simulada del backend" class="min-w-72">
          <UiSelect v-model="simulation" :options="simulationOptions" />
        </UiFormField>
        <UiButton @click="openModal(false)">
          Nueva área
        </UiButton>
        <UiButton variant="secondary" @click="openModal(true)">
          Detalle con pestañas
        </UiButton>
        <UiButton variant="danger" @click="toggle.ask(rows[0]!)">
          Desactivar / reactivar (con motivo)
        </UiButton>
      </div>
      <UiAlert v-if="saved" class="mt-4" variant="success" :message="saved" />
      <UiAlert v-if="lastChange" class="mt-4" variant="info" :message="lastChange" />
    </UiCard>

    <UiCard
      title="Activación: historial y motivo"
      description="Nada se elimina, se desactiva. UiActivityTimeline (pestaña Actividad de UiFormModal :activity; aquí con eventos fijos) y UiActiveField (el motivo aparece al editar si el estado cambia; pruébalo en «Nueva área»)."
    >
      <UiActivityTimeline entity-type="lab_areas" :events="demoActivity" />
    </UiCard>

    <UiFormModal
      v-model:open="modalOpen"
      title="Nueva área"
      description="Los campos con * son obligatorios."
      :size="tabbedModal ? 'xl' : 'lg'"
      :submitting="isSubmitting"
      :form-error="formError"
      :tabs="tabbedModal ? demoTabs.slice(0, 3) : undefined"
      @submit="onSubmit"
    >
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <UiFormField name="code" label="Código" required>
          <UiTextInput placeholder="HEM" />
        </UiFormField>
        <UiFormField name="name" label="Nombre" required>
          <UiTextInput />
        </UiFormField>
        <UiFormField name="email" label="Correo de contacto">
          <UiTextInput type="email" />
        </UiFormField>
        <UiFormField name="area" label="Área padre" required>
          <UiSelect :options="areaOptions" placeholder="Seleccionar área" />
        </UiFormField>
        <UiFormField name="capacity" label="Capacidad diaria" required>
          <UiTextInput type="number" min="1" />
        </UiFormField>
        <UiFormField name="notes" label="Notas" hint="Máximo 200 caracteres." class="sm:col-span-2">
          <UiTextarea />
        </UiFormField>
      </div>
      <!-- Demo en modo edición (estado guardado: activa): al desmarcar pide el motivo. -->
      <UiActiveField label="Activa" :initial="true" />
      <UiFormField name="confirmed">
        <UiCheckbox label="Confirmo que los datos son correctos" />
      </UiFormField>

      <template #children>
        <UiSection title="Hijos (pestaña fuera del form)" description="Cada pestaña distinta de la del form va fuera del form principal y puede tener su propio formulario; el botón Guardar del pie solo aparece en la pestaña del form.">
          <UiItemList :items="rows" :row-key="(row: DemoRow) => row.id">
            <template #default="{ item }">
              {{ item.name }}
            </template>
          </UiItemList>
        </UiSection>
      </template>
      <template #history>
        <p class="text-sm text-text-muted">Historial de cambios.</p>
      </template>

      <template v-if="!tabbedModal" #extra>
        <UiSection title="Sub-recurso (UiSection + UiItemList)" description="Fuera del form: aquí van los hijos de la entidad con sus propios formularios." divided>
          <template #actions>
            <UiButton variant="secondary" size="sm">
              Agregar
            </UiButton>
          </template>
          <UiItemList :items="rows" :row-key="(row: DemoRow) => row.id">
            <template #default="{ item }">
              {{ item.name }} <span class="text-text-muted">({{ item.code }})</span>
            </template>
            <template #trailing="{ item }">
              <UiStatusBadge :active="item.is_active" />
              <UiButton variant="ghost" size="sm">
                Editar
              </UiButton>
            </template>
          </UiItemList>
        </UiSection>
      </template>
    </UiFormModal>

    <UiToggleActiveModal :state="toggle" noun="el área" :name="toggle.target?.name" />
  </div>
</template>
