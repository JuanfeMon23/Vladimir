<script setup lang="ts">
const appConfig = useAppConfig()
const route = useRoute()

interface NavItem {
  label: string
  to: string
  /** Tag de Leo que lo habilita (los 8 módulos están protegidos: todo ítem lleva uno). */
  tag: string
}

// Módulos de negocio disponibles en el panel. Cada entrada nueva se agrega
// aquí a medida que se incorpora un módulo (layer) nuevo.
// `/_design` (referencia viva del sistema de diseño) queda fuera a propósito.
const navItems: NavItem[] = [
  { label: 'Personal', to: '/staff', tag: STAFF_TAGS.view },
  { label: 'Áreas', to: '/lab-areas', tag: LAB_AREAS_TAGS.view },
  { label: 'Exámenes', to: '/lab-tests', tag: LAB_TESTS_TAGS.view },
  { label: 'Precondiciones', to: '/preconditions', tag: PRECONDITIONS_TAGS.view },
  { label: 'Muestras', to: '/samples', tag: SAMPLES_TAGS.view },
  { label: 'Etiquetas de impresión', to: '/print-labels', tag: PRINT_LABELS_TAGS.view },
  { label: 'Analitos', to: '/analytes', tag: RESULT_TEMPLATES_TAGS.view },
  { label: 'Unidades de medida', to: '/units', tag: RESULT_TEMPLATES_TAGS.view },
  { label: 'Conjuntos de opciones', to: '/result-option-sets', tag: RESULT_TEMPLATES_TAGS.view },
  { label: 'Plantillas de resultados', to: '/result-templates', tag: RESULT_TEMPLATES_TAGS.view },
  { label: 'Documentos a firmar', to: '/consent-documents', tag: CONSENT_DOCUMENTS_TAGS.view }
]

const leoSession = useLeoSession()
const visibleNavItems = computed(() => navItems.filter(item => !item.tag || leoSession.can(item.tag)))

// Sidebar fuera de pantalla en < lg; se cierra al navegar.
const sidebarOpen = ref(false)
watch(() => route.fullPath, () => {
  sidebarOpen.value = false
})
</script>

<template>
  <div class="flex min-h-screen bg-background">
    <div
      v-if="sidebarOpen"
      class="fixed inset-0 z-30 bg-default-900/30 backdrop-blur-sm lg:hidden"
      aria-hidden="true"
      @click="sidebarOpen = false"
    />

    <aside
      class="fixed inset-y-0 left-0 z-40 flex w-64 shrink-0 flex-col bg-surface shadow-md transition-transform duration-200 ease-out lg:sticky lg:top-0 lg:h-screen lg:translate-x-0 lg:shadow-none lg:border-r lg:border-border"
      :class="sidebarOpen ? 'translate-x-0' : '-translate-x-full'"
      aria-label="Navegación principal"
    >
      <div class="flex h-14 items-center gap-3 px-5">
        <NuxtLink
          to="/"
          class="flex items-center gap-2.5 rounded-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-500"
        >
          <span class="flex h-8 w-8 items-center justify-center rounded-md bg-primary-500 text-sm font-bold text-text-inverted">
            {{ appConfig.name.charAt(0) }}
          </span>
          <span class="text-base font-semibold text-text">{{ appConfig.name }}</span>
        </NuxtLink>
      </div>

      <nav class="flex-1 space-y-0.5 overflow-y-auto px-3 pb-4">
        <p class="px-3 pb-1.5 pt-2 text-xs font-medium text-text-muted">
          Módulos
        </p>
        <NuxtLink
          v-for="item in visibleNavItems"
          :key="item.to"
          :to="item.to"
          class="flex h-9 items-center rounded-md px-3 text-sm font-medium text-default-600 transition duration-150 hover:bg-default-100 hover:text-text active:scale-[0.98] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-500"
          active-class="bg-primary-50! text-primary-700! font-semibold"
        >
          {{ item.label }}
        </NuxtLink>
      </nav>
    </aside>

    <div class="flex min-w-0 flex-1 flex-col">
      <LeoTopBar>
        <template #start>
          <UiButton
            class="lg:hidden"
            variant="ghost"
            size="sm"
            icon-only
            aria-label="Abrir menú"
            :aria-expanded="sidebarOpen"
            @click="sidebarOpen = !sidebarOpen"
          >
            <svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M2 4.75A.75.75 0 0 1 2.75 4h14.5a.75.75 0 0 1 0 1.5H2.75A.75.75 0 0 1 2 4.75Zm0 5.25a.75.75 0 0 1 .75-.75h14.5a.75.75 0 0 1 0 1.5H2.75A.75.75 0 0 1 2 10Zm0 5.25a.75.75 0 0 1 .75-.75h14.5a.75.75 0 0 1 0 1.5H2.75a.75.75 0 0 1-.75-.75Z" clip-rule="evenodd" />
            </svg>
          </UiButton>
        </template>
      </LeoTopBar>

      <main class="flex-1 p-4 sm:p-6">
        <slot />
      </main>
    </div>
  </div>
</template>
