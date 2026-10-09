import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { fakePage } from '~/testing/fakeApi'
import { flushAll } from '~/testing/dom'
import { useResultTemplateVersionContent } from '../composables/useResultTemplateVersionContent'
import ResultTemplateReportPreview from './ResultTemplateReportPreview.vue'

const fake = await vi.hoisted(async () => (await import('~/testing/fakeApi')).createFakeApi())
mockNuxtImport('useApi', () => () => fake.api)

enableAutoUnmount(afterEach)

const BASE = '/result-templates/t1/versions/v1'

const ANALYTES = [
  { id: 'ta1', analyte_id: 'an1', section_id: 's1', sort_order: 1, result_type: 'numeric', unit_id: 'u1', decimals: 0, option_set_id: null, is_required: true, is_reportable: true, is_active: true },
  { id: 'ta2', analyte_id: 'an2', section_id: 's1', sort_order: 2, result_type: 'titer', unit_id: null, decimals: null, option_set_id: 'os1', is_required: true, is_reportable: true, is_active: true },
  { id: 'ta3', analyte_id: 'an1', section_id: null, sort_order: 3, result_type: 'text', unit_id: null, decimals: null, option_set_id: null, is_required: false, is_reportable: false, is_active: false }
]

/** Rango como lo devuelve el backend (campos sin valor en `null`). */
const NO_VALUES = {
  sex: 'any', age_min: null, age_max: null, age_unit: null, condition: null, low: null, high: null,
  critical_low: null, critical_high: null, expected_option_id: null, expected_boolean: null,
  display_text: null, interpretation: null, is_active: true
}

beforeEach(() => {
  fake.reset()
  document.body.innerHTML = ''
  fake.routes[`GET ${BASE}/sections`] = [{ id: 's1', name: 'Serología', sort_order: 1, is_active: true }]
  fake.routes[`GET ${BASE}/analytes`] = ANALYTES
  fake.routes['GET /analytes'] = fakePage([
    { id: 'an1', code: 'GLU', name: 'Glucosa', is_active: true },
    { id: 'an2', code: 'VDRL', name: 'VDRL', is_active: true }
  ])
  fake.routes['GET /result-option-sets'] = fakePage([])
  fake.routes['GET /units'] = fakePage([{ id: 'u1', code: 'mg/dL', symbol: 'mg/dL', name: 'mg/dL', is_active: true }])
  fake.routes[`GET ${BASE}/analytes/ta1/reference-ranges`] = [
    { ...NO_VALUES, id: 'r1', template_analyte_id: 'ta1', low: 70, high: 110 }
  ]
  fake.routes[`GET ${BASE}/analytes/ta2/reference-ranges`] = [
    { ...NO_VALUES, id: 'r2', template_analyte_id: 'ta2', expected_option_id: 'o1' }
  ]
  fake.routes['GET /result-option-sets/os1/options'] = fakePage([{ id: 'o1', label: 'No reactivo' }])
})

const Host = defineComponent({
  setup() {
    const content = useResultTemplateVersionContent('t1', 'v1')
    onMounted(() => content.loadAll())
    return () => h(ResultTemplateReportPreview, { content })
  }
})

async function mountPreview() {
  const wrapper = await mountSuspended(Host, { attachTo: document.body })
  await flushAll(4)
  return wrapper
}

describe('ResultTemplateReportPreview', () => {
  it('muestra secciones, analitos, tipo, unidad y rangos formateados; deja fuera lo inactivo', async () => {
    const wrapper = await mountPreview()
    const text = wrapper.text()
    expect(text).toContain('Serología')
    expect(text).toContain('Glucosa (GLU)')
    expect(text).toContain('Numérico')
    expect(text).toContain('70 – 110 mg/dL')
    expect(text).toContain('VDRL (VDRL)')
    expect(text).toContain('Título (dilución)')
    expect(text).toContain('Esperado: No reactivo')
    // El analito inactivo (ta3, "Sin sección") no aparece ni consulta sus rangos.
    expect(text).not.toContain('Sin sección')
    expect(fake.requests).not.toHaveBeenCalledWith('GET', `${BASE}/analytes/ta3/reference-ranges`, expect.anything())
  })

  it('el orden de los analitos es el de la versión', async () => {
    const wrapper = await mountPreview()
    const names = wrapper.findAll('tbody th').map(th => th.text())
    expect(names[0]).toContain('Glucosa')
    expect(names[1]).toContain('VDRL')
  })

  it('sin analitos activos avisa que el reporte saldría vacío', async () => {
    fake.routes[`GET ${BASE}/analytes`] = []
    const wrapper = await mountPreview()
    expect(wrapper.text()).toContain('no tiene analitos activos')
  })

  it('si fallan los rangos muestra el error', async () => {
    fake.failures[`GET ${BASE}/analytes/ta1/reference-ranges`] = new Error('Sin conexión.')
    const wrapper = await mountPreview()
    expect(wrapper.text()).toContain('Sin conexión.')
  })
})
