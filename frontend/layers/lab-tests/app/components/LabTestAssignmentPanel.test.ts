import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import { ALL_LAB_TESTS_TAGS, LAB_TEST_SELECTOR_VIEW_TAGS } from '~/testing/session'
import { signInWith } from '#leo-client/testing/session'
import { buildLabTestAssignmentRows } from '../utils/assignmentRows'
import LabTestAssignmentPanel from './LabTestAssignmentPanel.vue'

const { getMock } = vi.hoisted(() => ({ getMock: vi.fn() }))
mockNuxtImport('useLeoAppApi', () => () => ({ get: getMock }))

const flush = async () => {
  for (let i = 0; i < 5; i++) await nextTick()
  await new Promise(resolve => setTimeout(resolve, 0))
}

describe('LabTestAssignmentPanel', () => {
  it('"Actividad" despliega el historial de la asignación de esa fila', async () => {
    getMock.mockResolvedValue({
      items: [{ id: 'e1', entity_type: 'lab_test_sample_types', entity_id: 'L-a', action: 'deactivated', reason: 'Ya no aplica', occurred_at: '2026-10-02T10:00:00Z' }],
      total: 1,
      page: 1,
      page_size: 20
    })
    const items = buildLabTestAssignmentRows(
      [{ id: 'a', linkId: 'L-a', isActive: true, sortOrder: 1 }],
      [{ id: 'a', label: 'Tubo rojo', isActive: true }, { id: 'b', label: 'Tubo lila', isActive: true }]
    )
    signInWith([...ALL_LAB_TESTS_TAGS, ...LAB_TEST_SELECTOR_VIEW_TAGS])
    const wrapper = await mountSuspended(LabTestAssignmentPanel, {
      props: {
        title: 'Tipos de muestra',
        items,
        activityEntityType: 'lab_test_sample_types',
        catalogModule: { tag: 'vladimir.samples.view', label: 'muestras' },
        saveTag: 'vladimir.lab-tests.set-sample-types'
      }
    })

    // Solo la fila con asignación tiene el botón.
    const buttons = wrapper.findAll('button').filter(b => b.text() === 'Actividad')
    expect(buttons).toHaveLength(1)
    expect(getMock).not.toHaveBeenCalled()

    await buttons[0]!.trigger('click')
    await flush()
    expect(getMock).toHaveBeenCalledWith('/activity', {
      params: { entity_type: 'lab_test_sample_types', entity_id: 'L-a', page: 1, page_size: 20 }
    })
    expect(wrapper.text()).toContain('Ya no aplica')
    expect(wrapper.text()).toContain('Ocultar actividad')
  })
})
