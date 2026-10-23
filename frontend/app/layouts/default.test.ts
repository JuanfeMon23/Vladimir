import { mountSuspended } from '@nuxt/test-utils/runtime'
import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import { signInWith } from '#leo-client/testing/session'
import DefaultLayout from './default.vue'

enableAutoUnmount(afterEach)

async function menuLabels(tags: string[]) {
  signInWith(tags)
  const wrapper = await mountSuspended(DefaultLayout)
  return wrapper.findAll('nav a').map(a => a.text())
}

describe('menú lateral por permiso', () => {
  it('con todos los view aparecen los 12 módulos, bajo la sección «Módulos»', async () => {
    const tags = [
      STAFF_TAGS.view, LAB_AREAS_TAGS.view, LAB_TESTS_TAGS.view, PRECONDITIONS_TAGS.view, SAMPLES_TAGS.view,
      PRINT_LABELS_TAGS.view, RESULT_TEMPLATES_TAGS.view, CONSENT_DOCUMENTS_TAGS.view, SETTINGS_TAGS.view
    ]
    signInWith(tags)
    const wrapper = await mountSuspended(DefaultLayout)
    expect(wrapper.findAll('nav a').map(a => a.text())).toEqual([
      'Personal', 'Áreas', 'Exámenes', 'Precondiciones', 'Muestras', 'Etiquetas de impresión',
      'Analitos', 'Unidades de medida', 'Conjuntos de opciones', 'Plantillas de resultados', 'Documentos a firmar', 'Ajustes del sistema'
    ])
    expect(wrapper.text()).toContain('Módulos')
    expect(wrapper.text()).toContain('Vladimir')
  })

  it('cada ítem lleva su icono SVG', async () => {
    signInWith([STAFF_TAGS.view, RESULT_TEMPLATES_TAGS.view])
    const wrapper = await mountSuspended(DefaultLayout)
    const links = wrapper.findAll('nav a')
    expect(links).toHaveLength(5)
    for (const link of links) expect(link.find('svg path').exists()).toBe(true)
  })

  it('con un solo view aparece únicamente su módulo; Plantillas comparte tag con Analitos, Unidades y Conjuntos', async () => {
    expect(await menuLabels([STAFF_TAGS.view])).toEqual(['Personal'])
    expect(await menuLabels([RESULT_TEMPLATES_TAGS.view])).toEqual([
      'Analitos', 'Unidades de medida', 'Conjuntos de opciones', 'Plantillas de resultados'
    ])
  })

  it('los permisos de acción no abren módulos por sí solos', async () => {
    expect(await menuLabels([STAFF_TAGS.create, LAB_TESTS_TAGS.edit])).toEqual([])
  })

  it('la app y el usuario aparecen en la barra superior de Leo', async () => {
    signInWith([STAFF_TAGS.view])
    const wrapper = await mountSuspended(DefaultLayout)
    expect(wrapper.find('[data-testid="leo-current-app"]').text()).toBe('Vladimir')
    expect(wrapper.text()).toContain('Ana Pérez')
  })
})
