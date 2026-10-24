<script setup lang="ts">
import type { UiSidebarItem } from '#andromeda/components/ui/UiSidebar.vue'

type NavItem = {
  label: string
  to: string
  /** Icono de trazo 24×24 (atributo `d` del path). */
  icon: string
} & (
  // Tag de Leo que lo habilita.
  | { tag: string }
  // Opt-in explícito a un ítem sin permiso; sin `tag` ni `public` no se muestra.
  | { public: true }
)

// Módulos de negocio disponibles en el panel. Cada entrada nueva se agrega
// aquí a medida que se incorpora un módulo (layer) nuevo.
// `/_design` (referencia viva del sistema de diseño) queda fuera a propósito.
const navItems: NavItem[] = [
  // Dos personas.
  { label: 'Personal', to: '/staff', tag: STAFF_TAGS.view, icon: 'M9 11a3.5 3.5 0 100-7 3.5 3.5 0 000 7zM2.5 20c0-3.5 2.7-5.5 6.5-5.5s6.5 2 6.5 5.5M16 4.5a3.5 3.5 0 010 6.5M18 14.8c2.2.6 3.5 2.3 3.5 5.2' },
  // Edificio.
  { label: 'Áreas', to: '/lab-areas', tag: LAB_AREAS_TAGS.view, icon: 'M5 21V8l7-4 7 4v13M3 21h18M9 21v-6h6v6' },
  // Matraz.
  { label: 'Exámenes', to: '/lab-tests', tag: LAB_TESTS_TAGS.view, icon: 'M9 3h6M10 3v6l-5.5 9.5A2 2 0 006.2 21h11.6a2 2 0 001.7-2.5L14 9V3' },
  // Lista con marcas.
  { label: 'Precondiciones', to: '/preconditions', tag: PRECONDITIONS_TAGS.view, icon: 'M9 6h11M9 12h11M9 18h11M3.5 6l1.5 1.5L7 5M3.5 12l1.5 1.5L7 11M3.5 18l1.5 1.5L7 17' },
  // Gota.
  { label: 'Muestras', to: '/samples', tag: SAMPLES_TAGS.view, icon: 'M12 2.5s6 6.2 6 10.5a6 6 0 01-12 0C6 8.7 12 2.5 12 2.5z' },
  // Etiqueta con ojal.
  { label: 'Etiquetas de impresión', to: '/print-labels', tag: PRINT_LABELS_TAGS.view, icon: 'M3 4h8.5L21 13.5 13.5 21 3 10.5zM8.5 8.5m-1 0a1 1 0 102 0 1 1 0 10-2 0' },
  // Molécula de tres nodos.
  { label: 'Analitos', to: '/analytes', tag: RESULT_TEMPLATES_TAGS.view, icon: 'M14 4a2 2 0 11-4 0 2 2 0 014 0zM7 19a2 2 0 11-4 0 2 2 0 014 0zM21 19a2 2 0 11-4 0 2 2 0 014 0zM12 6l-6 11.2M12 6l6 11.2M7 19h10' },
  // Regla en diagonal.
  { label: 'Unidades de medida', to: '/units', tag: RESULT_TEMPLATES_TAGS.view, icon: 'M3.5 16.5l13-13 4 4-13 13zM7.5 12.5l2 2M10.5 9.5l2 2M13.5 6.5l2 2' },
  // Tres opciones en columna.
  { label: 'Conjuntos de opciones', to: '/result-option-sets', tag: RESULT_TEMPLATES_TAGS.view, icon: 'M3 5h3v3H3zM3 11h3v3H3zM3 17h3v3H3zM9 6.5h12M9 12.5h12M9 18.5h12' },
  // Cuadro con encabezado y columna.
  { label: 'Plantillas de resultados', to: '/result-templates', tag: RESULT_TEMPLATES_TAGS.view, icon: 'M4 4h16v16H4zM4 9h16M9 9v11' },
  // Documento con firma.
  { label: 'Documentos a firmar', to: '/consent-documents', tag: CONSENT_DOCUMENTS_TAGS.view, icon: 'M6 3h8l4 4v14H6zM14 3v4h4M9 17c1-2 2-2 3 0s2 1 3-1' },
  // Controles deslizantes.
  { label: 'Ajustes del sistema', to: '/settings', tag: SETTINGS_TAGS.view, icon: 'M4 7h9M17 7h3M4 17h3M11 17h9M15 5v4M9 15v4' }
]

const leoSession = useLeoSession()
const menu = computed<UiSidebarItem[]>(() =>
  navItems
    .filter(item => ('tag' in item ? leoSession.can(item.tag) : item.public))
    .map(({ label, to, icon }) => ({ section: 'Módulos', label, to, icon }))
)
</script>

<template>
  <LeoAppShell
    :items="menu"
    brand="Vladimir"
    brand-to="/"
    storage-key="vladimir.sidebar.collapsed"
    content-width="full"
  >
    <slot />
  </LeoAppShell>
</template>
