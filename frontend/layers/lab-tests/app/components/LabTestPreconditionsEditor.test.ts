import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiRequestError } from '~/composables/useApi'
import { fakePage } from '~/testing/fakeApi'
import { control, flushAll, hasRow, rowOf, setChecked, setValue, submitForm } from '~/testing/dom'
import type { LabTestPreconditionOption, LabTestPreconditionRead } from '../types/lab-tests'
import LabTestPreconditionsEditor from './LabTestPreconditionsEditor.vue'

const fake = await vi.hoisted(async () => (await import('~/testing/fakeApi')).createFakeApi())
mockNuxtImport('useApi', () => () => fake.api)

enableAutoUnmount(afterEach)

const AYUNO = 'Ayuno (AYU)'
const AYUNO_8H = 'Ayuno 8 h (AYU8)'
const DIETA = 'Dieta (DIE)'
const DIETA_SAL = 'Sin sal (DIE1)'
const RETIRADA = 'Retirada (RET)'

function option(id: string, code: string, name: string, extra: Partial<LabTestPreconditionOption> = {}): LabTestPreconditionOption {
  return {
    id,
    code,
    name,
    category: 'fasting',
    description: null,
    duration_value: null,
    duration_unit: null,
    patient_instructions: null,
    is_active: true,
    items: [],
    ...extra
  }
}

function assigned(preconditionId: string, extra: Partial<LabTestPreconditionRead> = {}): LabTestPreconditionRead {
  return {
    id: `L-${preconditionId}`,
    precondition_id: preconditionId,
    is_mandatory: true,
    sort_order: 1,
    is_active: true,
    name: '',
    description: null,
    duration_value: null,
    duration_unit: null,
    patient_instructions: null,
    name_override: null,
    description_override: null,
    duration_value_override: null,
    duration_unit_override: null,
    patient_instructions_override: null,
    ...extra
  }
}

beforeEach(() => {
  fake.reset()
  document.body.innerHTML = ''
  fake.routes['GET /preconditions'] = fakePage([
    option('ayuno', 'AYU', 'Ayuno', {
      duration_value: 8,
      duration_unit: 'horas',
      patient_instructions: 'No comer',
      items: [option('ayuno8', 'AYU8', 'Ayuno 8 h')]
    }),
    // Raíz inactiva: ni ella ni sus ítems se ofrecen para agregar.
    option('dieta', 'DIE', 'Dieta', { is_active: false, items: [option('dieta1', 'DIE1', 'Sin sal')] }),
    option('retirada', 'RET', 'Retirada', { is_active: false })
  ])
  fake.routes['GET /lab-tests/t1/preconditions'] = [
    // Overrides crudos: duración 12 y unidad 'horas' (esta última igual al
    // catálogo: sigue siendo override y no se pierde); el resto, del catálogo.
    assigned('ayuno', {
      name: 'Ayuno',
      is_mandatory: false,
      duration_value: 12,
      duration_unit: 'horas',
      patient_instructions: 'No comer',
      duration_value_override: 12,
      duration_unit_override: 'horas',
      sort_order: 1
    }),
    // Asignada vigente a una precondición ya desactivada: se conserva.
    assigned('retirada', { name: 'Retirada', sort_order: 2 })
  ]
})

async function mountEditor() {
  const wrapper = await mountSuspended(LabTestPreconditionsEditor, { props: { labTestId: 't1' }, attachTo: document.body })
  await flushAll()
  const root = wrapper.element.parentElement as HTMLElement
  return { root, form: root.querySelector('form')! }
}

describe('LabTestPreconditionsEditor', () => {
  it('carga los overrides crudos del backend (aunque coincidan con el catálogo)', async () => {
    const { root } = await mountEditor()
    const ayuno = rowOf(root, AYUNO)
    expect(control(ayuno, AYUNO).checked).toBe(true)
    expect(control(ayuno, 'Obligatoria').checked).toBe(false)
    expect(control(ayuno, 'Nombre (override)').value).toBe('')
    expect(control(ayuno, 'Instrucciones al paciente (override)').value).toBe('')
    expect(control(ayuno, 'Duración (override)').value).toBe('12')
    expect(control(ayuno, 'Descripción (override)').value).toBe('')
    expect(control<HTMLSelectElement>(ayuno, 'Unidad de duración (override)').value).toBe('horas')
  })

  it('ofrece ítems de raíces activas y conserva la asignada inactiva', async () => {
    const { root } = await mountEditor()
    expect(hasRow(root, AYUNO_8H)).toBe(true)
    expect(hasRow(root, DIETA)).toBe(false)
    expect(hasRow(root, DIETA_SAL)).toBe(false)
    const retirada = rowOf(root, RETIRADA)
    expect(control(retirada, RETIRADA).checked).toBe(true)
    expect(retirada.textContent).toContain('Inactivo')
  })

  it('el PUT envía el set completo con overrides y sort_order según la lista', async () => {
    const { root, form } = await mountEditor()
    await setChecked(root, AYUNO_8H, true)
    const item = rowOf(root, AYUNO_8H)
    await setValue(control(item, 'Nombre (override)'), 'Ayuno corto')
    await setValue(control<HTMLSelectElement>(item, 'Unidad de duración (override)'), 'minutos')

    await submitForm(form)
    expect(fake.bodies('PUT', '/lab-tests/t1/preconditions')).toEqual([[
      {
        precondition_id: 'ayuno',
        is_mandatory: false,
        name_override: null,
        description_override: null,
        duration_value_override: 12,
        duration_unit_override: 'horas',
        patient_instructions_override: null,
        sort_order: 1
      },
      {
        precondition_id: 'retirada',
        is_mandatory: true,
        name_override: null,
        description_override: null,
        duration_value_override: null,
        duration_unit_override: null,
        patient_instructions_override: null,
        sort_order: 2
      },
      {
        precondition_id: 'ayuno8',
        is_mandatory: true,
        name_override: 'Ayuno corto',
        description_override: null,
        duration_value_override: null,
        duration_unit_override: 'minutos',
        patient_instructions_override: null,
        sort_order: 3
      }
    ]])
    expect(root.textContent).toContain('Precondiciones guardadas.')
  })

  it('desmarcar quita la precondición del PUT y limpia sus overrides', async () => {
    const { root, form } = await mountEditor()
    await setChecked(root, AYUNO, false)
    await submitForm(form)
    expect((fake.bodies('PUT', '/lab-tests/t1/preconditions')[0] as { precondition_id: string }[]).map(i => i.precondition_id))
      .toEqual(['retirada'])

    await setChecked(root, AYUNO, true)
    expect(control(rowOf(root, AYUNO), 'Duración (override)').value).toBe('')
  })

  it('un override de duración inválido no envía y se marca en su campo', async () => {
    const { root, form } = await mountEditor()
    await setValue(control(rowOf(root, AYUNO), 'Duración (override)'), '-2')
    await submitForm(form)
    expect(fake.bodies('PUT', '/lab-tests/t1/preconditions')).toEqual([])
    expect(rowOf(root, AYUNO).textContent).toContain('Debe ser mayor o igual a 0.')
  })

  it('el 422 inactive_reference se muestra en el aviso del formulario', async () => {
    fake.failures['PUT /lab-tests/t1/preconditions'] = new ApiRequestError(
      { code: 'inactive_reference', message: 'La precondición «AYU8» está inactiva.', details: { precondition_id: 'ayuno8' } },
      422
    )
    const { root, form } = await mountEditor()
    await setChecked(root, AYUNO_8H, true)
    await submitForm(form)
    expect(form.querySelector('[role="alert"]')?.textContent).toContain('La precondición «AYU8» está inactiva.')
  })
})
